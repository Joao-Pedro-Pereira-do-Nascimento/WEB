"""Armazenamento no Firebase **Realtime Database** (RTDB) via ``firebase-admin``.

Ativação: em ``st.secrets`` (``.streamlit/secrets.toml``), a seção ``[firebase]``
com os campos da conta de serviço **e** ``database_url``. Exemplo em
``.streamlit/secrets.toml.example``.

Estrutura no banco (tudo debaixo de ``/uno``)::

    /uno/rooms/{CODIGO}     -> {"version": n, "data": "<JSON da sala>", "updated_at": ts}
    /uno/presence/{CODIGO}  -> {id_do_jogador: timestamp, ...}
    /uno/stats/{chave}      -> {"name": ..., "games": n, "wins": n, ...}
    /uno/stats_games/{id}   -> marca de partida já contada no ranking (idempotência)
    /uno/users/{chave}      -> conta (senha só como hash PBKDF2 + salt), em {"data": "<JSON>"}
    /uno/sessions/{hash}    -> sessão de login (só o hash SHA-256 do token) com validade
    /uno/limits/{chave}     -> tentativas erradas de login/redefinição (janela de 15 min)

As chaves de jogador são o nome normalizado (minúsculas, sem acento; veja
``game.rooms.name_key``) e ainda escapadas por ``safe_key`` — o nome original
fica no campo ``name`` para exibição. Bots nunca entram no ranking.

Por que o estado da sala é uma *string* JSON? O RTDB não aceita chaves com
``. $ # [ ] /``, descarta listas vazias e valores ``None`` e transforma listas em
objetos. Guardar o JSON como texto mantém o estado exatamente igual ao dos
outros armazenamentos.

Concorrência: cada jogada usa ``reference.transaction()``. O RTDB lê o valor
atual (com ETag), roda a função e só grava se ninguém tiver escrito no meio;
se alguém escreveu, a função roda de novo com o estado novo — e a validação do
motor (``game/engine.py``) decide quem jogou primeiro (a segunda jogada
fora da vez é recusada).
"""

from __future__ import annotations

import json
import threading
import time
from typing import Any, Callable

from .base import STAT_FIELDS, Backend, RoomNotFound

ROOT = "uno"
CACHE_TTL = 0.8
FORBIDDEN = set(".$#[]/%") | {chr(c) for c in range(32)} | {chr(127)}


def safe_key(key: str) -> str:
    """Escapa caracteres proibidos em chaves do RTDB (``%2E`` para ``.`` etc.)."""
    key = str(key)
    out = "".join(f"%{ord(ch):02X}" if ch in FORBIDDEN else ch for ch in key)
    return out or "_"


class _Exists(Exception):
    pass


class RTDBBackend(Backend):
    name = "rtdb"
    poll_seconds = 2.0

    def __init__(self, service_account: dict | None, database_url: str,
                 app_name: str = "uno-folclouno-rtdb", db_module=None, app=None):
        """``db_module``/``app`` permitem injetar um banco falso nos testes."""
        if not database_url:
            raise ValueError("database_url vazio")
        if db_module is None:
            import firebase_admin
            from firebase_admin import credentials, db

            info = dict(service_account or {})
            info.pop("database_url", None)
            info.pop("databaseURL", None)
            if "private_key" in info:  # secrets às vezes chegam com "\n" literal
                info["private_key"] = info["private_key"].replace("\\n", "\n")
            try:
                app = firebase_admin.get_app(app_name)
            except ValueError:
                app = firebase_admin.initialize_app(credentials.Certificate(info),
                                                    {"databaseURL": database_url}, name=app_name)
            db_module = db
        self._db = db_module
        self._app = app
        self.database_url = database_url
        self._cache: dict[str, tuple[float, Any]] = {}
        self._lock = threading.Lock()
        self._last_cleanup = -1e9

    # ------------------------------------------------------------ util
    def _ref(self, *parts: str):
        path = "/".join([ROOT, *(safe_key(p) for p in parts)])
        return self._db.reference(path, app=self._app)

    def _cached(self, key: str, loader: Callable[[], Any], ttl: float = CACHE_TTL) -> Any:
        now = time.monotonic()
        with self._lock:
            hit = self._cache.get(key)
            if hit and now - hit[0] < ttl:
                return hit[1]
        value = loader()
        with self._lock:
            self._cache[key] = (time.monotonic(), value)
        return value

    def _invalidate(self, key: str, value: Any = None) -> None:
        with self._lock:
            if value is None:
                self._cache.pop(key, None)
            else:
                self._cache[key] = (time.monotonic(), value)

    @staticmethod
    def _decode(node) -> dict | None:
        if not node or not isinstance(node, dict) or "data" not in node:
            return None
        state = json.loads(node["data"])
        state["version"] = node.get("version", state.get("version", 0))
        return state

    @staticmethod
    def _encode(state: dict) -> dict:
        return {"version": state["version"], "data": json.dumps(state, ensure_ascii=False),
                "updated_at": state.get("updated_at", time.time())}

    # ------------------------------------------------------------ salas
    def create_room(self, code: str, state: dict) -> bool:
        state = dict(state)
        state["version"] = 1
        state["updated_at"] = time.time()

        def update(current):
            if current is not None:
                raise _Exists()
            return self._encode(state)

        try:
            self._ref("rooms", code).transaction(update)
        except _Exists:
            return False
        self._invalidate("room:" + code, state)
        return True

    def get_room(self, code: str) -> dict | None:
        ref = self._ref("rooms", code)
        state = self._cached("room:" + code, lambda: self._decode(ref.get()))
        return json.loads(json.dumps(state)) if state is not None else None  # cópia

    def transact(self, code: str, fn: Callable[[dict], Any]) -> tuple[dict, Any]:
        box: dict[str, Any] = {}

        def update(current):
            state = self._decode(current)  # roda de novo a cada repetição, com o valor novo
            if state is None:
                raise RoomNotFound(code)
            version = state.get("version", 0)
            result = fn(state)  # exceção => transação abortada, nada é gravado
            state["version"] = version + 1
            state["updated_at"] = time.time()
            box["state"], box["result"] = state, result
            return self._encode(state)

        self._ref("rooms", code).transaction(update)
        self._invalidate("room:" + code, box["state"])
        return box["state"], box["result"]

    def delete_room(self, code: str) -> None:
        self._ref("rooms", code).delete()
        self._ref("presence", code).delete()
        self._invalidate("room:" + code)

    # ------------------------------------------------------------ presença
    def heartbeat(self, code: str, pid: str, ts: float) -> None:
        self._ref("presence", code, pid).set(ts)

    def presence(self, code: str) -> dict[str, float]:
        ref = self._ref("presence", code)
        return dict(self._cached("presence:" + code, lambda: ref.get() or {}, ttl=3.0))

    # ------------------------------------------------------------ estatísticas
    def record_stats(self, entries: list[tuple[str, str, dict]], game_id: str | None = None) -> None:
        """Incremento atômico por jogador (``transaction``). Com ``game_id`` é idempotente:
        a partida é marcada em ``/uno/stats_games`` e, se já estiver lá, nada é somado."""
        if game_id:
            def mark(current):
                if current is not None:
                    raise _Exists()
                return {"at": time.time(), "players": len(entries)}

            try:
                self._ref("stats_games", game_id).transaction(mark)
            except _Exists:
                return
        for key, name, inc in entries:
            def update(current, name=name, inc=inc):
                row = dict(current) if isinstance(current, dict) else {}
                for f in STAT_FIELDS:
                    row.setdefault(f, 0)
                row["name"] = name
                for field, value in inc.items():
                    if field in STAT_FIELDS:
                        row[field] = int(row.get(field, 0)) + int(value)
                row["updated_at"] = time.time()
                return row

            self._ref("stats", key).transaction(update)
        self._invalidate("ranking")

    def ranking(self) -> list[dict]:
        def load():
            data = self._ref("stats").get() or {}
            rows = []
            for k, v in data.items():
                if not isinstance(v, dict):
                    continue
                row = {f: 0 for f in STAT_FIELDS}
                row.update(v)
                row["key"] = k
                rows.append(row)
            rows.sort(key=lambda r: (-r.get("wins", 0), -r.get("points", 0), r.get("name", "")))
            return rows[:300]

        return self._cached("ranking", load, ttl=10.0)

    # ------------------------------------------------------------ documentos (contas, sessões)
    # /uno/users/{chave}, /uno/sessions/{hash}, /uno/limits/{chave} -> {"data": "<JSON>"}
    def doc_get(self, coll: str, key: str) -> dict | None:
        node = self._ref(coll, key).get()
        if not isinstance(node, dict) or "data" not in node:
            return None
        return json.loads(node["data"])

    def doc_update(self, coll: str, key: str, fn) -> Any:
        box: dict[str, Any] = {}

        def update(current):
            cur = json.loads(current["data"]) if isinstance(current, dict) and "data" in current else None
            new, box["result"] = fn(cur)  # repete com o valor novo se alguém gravou no meio
            if new is None:
                return None
            return {"data": json.dumps(new, ensure_ascii=False), "updated_at": time.time()}

        self._ref(coll, key).transaction(update)
        return box.get("result")

    def cleanup(self, max_age_hours: float = 48) -> int:
        """Remove salas paradas há muito tempo (chamado ao criar sala; no máximo 1x por hora)."""
        if time.monotonic() - self._last_cleanup < 3600:
            return 0
        self._last_cleanup = time.monotonic()
        try:
            rooms = self._ref("rooms").get(shallow=True) or {}
        except TypeError:
            rooms = self._ref("rooms").get() or {}
        except Exception:
            return 0
        limit = time.time() - max_age_hours * 3600
        removed = 0
        for code in list(rooms)[:200]:
            try:
                ts = self._ref("rooms", code, "updated_at").get() or 0
                if ts and ts < limit:
                    self.delete_room(code)
                    removed += 1
            except Exception:
                pass
        return removed
