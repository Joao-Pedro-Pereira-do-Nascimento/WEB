"""Armazenamento em arquivos JSON com trava de arquivo.

Funciona com várias abas, vários dispositivos na mesma rede (todos acessando o
mesmo servidor Streamlit) e até no Streamlit Cloud (os dados somem quando o
app reinicia — para persistência de verdade, use o Firebase).
"""

from __future__ import annotations

import contextlib
import json
import os
import time
from pathlib import Path
from typing import Any, Callable

from .base import STAT_FIELDS, Backend, RoomNotFound

try:  # Linux / macOS
    import fcntl

    def _lock(f):
        fcntl.flock(f.fileno(), fcntl.LOCK_EX)

    def _unlock(f):
        fcntl.flock(f.fileno(), fcntl.LOCK_UN)
except ImportError:  # Windows
    import msvcrt

    def _lock(f):
        f.seek(0)
        while True:
            try:
                msvcrt.locking(f.fileno(), msvcrt.LK_LOCK, 1)
                return
            except OSError:
                time.sleep(0.01)

    def _unlock(f):
        f.seek(0)
        msvcrt.locking(f.fileno(), msvcrt.LK_UNLCK, 1)


class LocalBackend(Backend):
    name = "local"
    poll_seconds = 1.2

    def __init__(self, root: str | os.PathLike = ".data"):
        self.root = Path(root)
        (self.root / "rooms").mkdir(parents=True, exist_ok=True)
        (self.root / "presence").mkdir(parents=True, exist_ok=True)

    # ------------------------------------------------------------ utilidades
    def _room_path(self, code: str) -> Path:
        return self.root / "rooms" / f"{code}.json"

    @contextlib.contextmanager
    def _locked(self, path: Path):
        lock_path = path.with_suffix(path.suffix + ".lock")
        with open(lock_path, "a+") as lf:
            _lock(lf)
            try:
                yield
            finally:
                _unlock(lf)

    @staticmethod
    def _read(path: Path) -> Any:
        try:
            with open(path, encoding="utf-8") as f:
                return json.load(f)
        except FileNotFoundError:
            return None

    @staticmethod
    def _write(path: Path, data: Any) -> None:
        tmp = path.with_suffix(f".{os.getpid()}.{time.monotonic_ns()}.tmp")
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False)
        os.replace(tmp, path)  # troca atômica: leitores nunca veem arquivo pela metade

    # ------------------------------------------------------------ salas
    def create_room(self, code: str, state: dict) -> bool:
        path = self._room_path(code)
        with self._locked(path):
            if path.exists():
                return False
            state = dict(state)
            state["version"] = 1
            self._write(path, state)
            return True

    def get_room(self, code: str) -> dict | None:
        return self._read(self._room_path(code))

    def transact(self, code: str, fn: Callable[[dict], Any]) -> tuple[dict, Any]:
        path = self._room_path(code)
        with self._locked(path):
            state = self._read(path)
            if state is None:
                raise RoomNotFound(code)
            version = state.get("version", 0)
            result = fn(state)  # exceção => nada é gravado
            state["version"] = version + 1
            state["updated_at"] = time.time()
            self._write(path, state)
            return state, result

    # ------------------------------------------------------------ presença
    def heartbeat(self, code: str, pid: str, ts: float) -> None:
        path = self.root / "presence" / f"{code}.json"
        with self._locked(path):
            data = self._read(path) or {}
            data[pid] = ts
            self._write(path, data)

    def presence(self, code: str) -> dict[str, float]:
        return self._read(self.root / "presence" / f"{code}.json") or {}

    # ------------------------------------------------------------ estatísticas
    def record_stats(self, entries: list[tuple[str, str, dict]], game_id: str | None = None) -> None:
        if game_id:
            gpath = self.root / "stats_games.json"
            with self._locked(gpath):
                done = self._read(gpath) or {}
                if game_id in done:
                    return  # partida já contada
                done[game_id] = time.time()
                self._write(gpath, done)
        path = self.root / "stats.json"
        with self._locked(path):
            data = self._read(path) or {}
            for key, name, inc in entries:
                row = data.setdefault(key, {f: 0 for f in STAT_FIELDS})
                row["name"] = name
                for field, value in inc.items():
                    if field in STAT_FIELDS:
                        row[field] = row.get(field, 0) + int(value)
                row["updated_at"] = time.time()
            self._write(path, data)

    def ranking(self) -> list[dict]:
        data = self._read(self.root / "stats.json") or {}
        rows = [dict(v, key=k) for k, v in data.items()]
        rows.sort(key=lambda r: (-r.get("wins", 0), -r.get("points", 0), r.get("name", "")))
        return rows

    # ------------------------------------------------------------ documentos (contas, sessões)
    def _doc_path(self, coll: str, key: str) -> Path:
        from urllib.parse import quote

        folder = self.root / "docs" / coll
        folder.mkdir(parents=True, exist_ok=True)
        return folder / (quote(str(key), safe="") + ".json")

    def doc_get(self, coll: str, key: str) -> dict | None:
        return self._read(self._doc_path(coll, key))

    def doc_update(self, coll: str, key: str, fn) -> Any:
        path = self._doc_path(coll, key)
        with self._locked(path):
            new, result = fn(self._read(path))
            if new is None:
                with contextlib.suppress(FileNotFoundError):
                    path.unlink()
            else:
                self._write(path, new)
            return result

    def cleanup(self, max_age_hours: float = 48) -> int:
        """Remove salas antigas (chamado ao criar sala)."""
        removed = 0
        limit = time.time() - max_age_hours * 3600
        for path in (self.root / "rooms").glob("*.json"):
            try:
                if path.stat().st_mtime < limit:
                    path.unlink()
                    removed += 1
            except OSError:
                pass
        return removed
