"""Armazenamento no Cloud Firestore (Firebase) via ``firebase-admin``.

Credenciais: o dicionário da conta de serviço em ``st.secrets["firebase"]``
(veja ``.streamlit/secrets.toml.example`` e o README).

Estrutura no Firestore:
    uno_rooms/{CODIGO}     -> {version, data (JSON da sala), updated_at}
    uno_presence/{CODIGO}  -> {id_do_jogador: timestamp, ...}
    uno_stats/{nome}       -> contadores acumulados por jogador

Cada jogada roda dentro de uma transação do Firestore: se dois jogadores
agirem ao mesmo tempo, o Firestore repete a transação com o estado novo e a
validação do motor decide quem jogou primeiro (concorrência otimista).
"""

from __future__ import annotations

import json
import threading
import time
from typing import Any, Callable

from .base import STAT_FIELDS, Backend, RoomNotFound

ROOMS = "uno_rooms"
PRESENCE = "uno_presence"
STATS = "uno_stats"
CACHE_TTL = 0.8  # todas as sessões do mesmo servidor compartilham leituras recentes


class _Abort(Exception):
    """Transporta a exceção do motor para fora da transação."""

    def __init__(self, inner: BaseException):
        super().__init__(str(inner))
        self.inner = inner


class FirebaseBackend(Backend):
    name = "firebase"
    poll_seconds = 2.0

    def __init__(self, service_account: dict, app_name: str = "uno-folclouno"):
        import firebase_admin
        from firebase_admin import credentials, firestore

        info = dict(service_account)
        if "private_key" in info:  # secrets às vezes chegam com "\n" literal
            info["private_key"] = info["private_key"].replace("\\n", "\n")
        try:
            app = firebase_admin.get_app(app_name)
        except ValueError:
            app = firebase_admin.initialize_app(credentials.Certificate(info), name=app_name)
        self.db = firestore.client(app)
        self._fs = firestore
        self._cache: dict[str, tuple[float, Any]] = {}
        self._lock = threading.Lock()

    # ------------------------------------------------------------ cache
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
    def _decode(snap) -> dict | None:
        if not snap.exists:
            return None
        doc = snap.to_dict()
        state = json.loads(doc["data"])
        state["version"] = doc.get("version", state.get("version", 0))
        return state

    # ------------------------------------------------------------ salas
    def create_room(self, code: str, state: dict) -> bool:
        from google.api_core.exceptions import AlreadyExists

        state = dict(state)
        state["version"] = 1
        try:
            self.db.collection(ROOMS).document(code).create(
                {"version": 1, "data": json.dumps(state, ensure_ascii=False), "updated_at": time.time()}
            )
        except AlreadyExists:
            return False
        self._invalidate("room:" + code, state)
        return True

    def get_room(self, code: str) -> dict | None:
        ref = self.db.collection(ROOMS).document(code)
        state = self._cached("room:" + code, lambda: self._decode(ref.get()))
        return json.loads(json.dumps(state)) if state is not None else None  # cópia

    def transact(self, code: str, fn: Callable[[dict], Any]) -> tuple[dict, Any]:
        ref = self.db.collection(ROOMS).document(code)
        firestore = self._fs
        box: dict[str, Any] = {}

        @firestore.transactional
        def run(transaction):
            snap = ref.get(transaction=transaction)
            state = self._decode(snap)
            if state is None:
                raise RoomNotFound(code)
            version = state.get("version", 0)
            try:
                result = fn(state)
            except Exception as exc:  # regra violada: não grava nada
                raise _Abort(exc) from exc
            state["version"] = version + 1
            state["updated_at"] = time.time()
            transaction.set(ref, {
                "version": state["version"],
                "data": json.dumps(state, ensure_ascii=False),
                "updated_at": state["updated_at"],
            })
            box["state"], box["result"] = state, result

        try:
            run(self.db.transaction(max_attempts=8))
        except _Abort as abort:
            raise abort.inner
        self._invalidate("room:" + code, box["state"])
        return box["state"], box["result"]

    # ------------------------------------------------------------ documentos (contas, sessões)
    def doc_get(self, coll: str, key: str) -> dict | None:
        snap = self.db.collection(f"uno_{coll}").document(key).get()
        return json.loads(snap.to_dict()["data"]) if snap.exists else None

    def doc_update(self, coll: str, key: str, fn) -> Any:
        ref = self.db.collection(f"uno_{coll}").document(key)
        firestore = self._fs
        box: dict[str, Any] = {}

        @firestore.transactional
        def run(transaction):
            snap = ref.get(transaction=transaction)
            cur = json.loads(snap.to_dict()["data"]) if snap.exists else None
            try:
                new, box["result"] = fn(cur)
            except Exception as exc:
                raise _Abort(exc) from exc
            if new is None:
                if snap.exists:
                    transaction.delete(ref)
            else:
                transaction.set(ref, {"data": json.dumps(new, ensure_ascii=False), "updated_at": time.time()})

        try:
            run(self.db.transaction(max_attempts=8))
        except _Abort as abort:
            raise abort.inner
        return box.get("result")

    # ------------------------------------------------------------ presença
    def heartbeat(self, code: str, pid: str, ts: float) -> None:
        self.db.collection(PRESENCE).document(code).set({pid: ts}, merge=True)

    def presence(self, code: str) -> dict[str, float]:
        ref = self.db.collection(PRESENCE).document(code)

        def load():
            snap = ref.get()
            return (snap.to_dict() or {}) if snap.exists else {}

        return dict(self._cached("presence:" + code, load, ttl=3.0))

    # ------------------------------------------------------------ estatísticas
    def record_stats(self, entries: list[tuple[str, str, dict]], game_id: str | None = None) -> None:
        if game_id:
            from google.api_core.exceptions import AlreadyExists

            try:  # marca a partida; se já existir, ela já foi contada
                self.db.collection("uno_stats_games").document(game_id.replace("/", "_")).create({"at": time.time()})
            except AlreadyExists:
                return
        batch = self.db.batch()
        for key, name, inc in entries:
            data: dict[str, Any] = {"name": name, "updated_at": time.time()}
            for field, value in inc.items():
                if field in STAT_FIELDS:
                    data[field] = self._fs.Increment(int(value))
            batch.set(self.db.collection(STATS).document(key), data, merge=True)
        batch.commit()
        self._invalidate("ranking")

    def ranking(self) -> list[dict]:
        def load():
            rows = []
            for snap in self.db.collection(STATS).limit(300).stream():
                row = {f: 0 for f in STAT_FIELDS}
                row.update(snap.to_dict() or {})
                row["key"] = snap.id
                rows.append(row)
            rows.sort(key=lambda r: (-r.get("wins", 0), -r.get("points", 0), r.get("name", "")))
            return rows

        return self._cached("ranking", load, ttl=10.0)
