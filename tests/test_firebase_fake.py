"""FirebaseBackend testado com um Firestore falso em memória (sem rede).

O cliente falso imita o necessário da API do google-cloud-firestore:
documentos, ``create`` (AlreadyExists), ``set(merge=)``, ``Increment``,
lotes e transações otimistas com repetição em caso de conflito.
"""

import copy
import threading

import pytest

pytest.importorskip("firebase_admin")

from google.api_core.exceptions import AlreadyExists  # noqa: E402

from game import rooms as R  # noqa: E402
from storage import NoChange, RoomNotFound  # noqa: E402
from storage import firebase as FB  # noqa: E402


class Increment:
    def __init__(self, value):
        self.value = value


class Snap:
    def __init__(self, doc_id, data):
        self.id = doc_id
        self._data = copy.deepcopy(data)
        self.exists = data is not None

    def to_dict(self):
        return copy.deepcopy(self._data)


class Store:
    def __init__(self):
        self.docs = {}      # (col, id) -> dict
        self.stamp = {}     # (col, id) -> nº de escritas
        self.lock = threading.RLock()

    def write(self, key, data, merge=False):
        with self.lock:
            cur = dict(self.docs.get(key) or {}) if merge else {}
            for k, v in data.items():
                if isinstance(v, Increment):
                    cur[k] = cur.get(k, 0) + v.value
                else:
                    cur[k] = v
            self.docs[key] = cur
            self.stamp[key] = self.stamp.get(key, 0) + 1


class Ref:
    def __init__(self, store, col, doc_id):
        self.store, self.key, self.id = store, (col, doc_id), doc_id

    def get(self, transaction=None):
        with self.store.lock:
            if transaction is not None:
                transaction.reads[self.key] = self.store.stamp.get(self.key, 0)
            return Snap(self.id, self.store.docs.get(self.key))

    def create(self, data):
        with self.store.lock:
            if self.key in self.store.docs:
                raise AlreadyExists("existe")
            self.store.write(self.key, data)

    def set(self, data, merge=False):
        self.store.write(self.key, data, merge)


class Query:
    def __init__(self, store, col):
        self.store, self.col = store, col

    def limit(self, n):
        return self

    def stream(self):
        with self.store.lock:
            items = [(k[1], v) for k, v in self.store.docs.items() if k[0] == self.col]
        return [Snap(i, v) for i, v in items]


class Collection(Query):
    def document(self, doc_id):
        return Ref(self.store, self.col, doc_id)


class Batch:
    def __init__(self, store):
        self.store, self.ops = store, []

    def set(self, ref, data, merge=False):
        self.ops.append((ref.key, data, merge))

    def commit(self):
        with self.store.lock:
            for key, data, merge in self.ops:
                self.store.write(key, data, merge)


class Conflict(Exception):
    pass


class Transaction:
    def __init__(self, store, max_attempts=5):
        self.store, self.max_attempts = store, max_attempts
        self.reads, self.writes = {}, []
        self.attempts = 0

    def set(self, ref, data, merge=False):
        self.writes.append((ref.key, data, merge))

    def commit(self):
        with self.store.lock:
            for key, stamp in self.reads.items():
                if self.store.stamp.get(key, 0) != stamp:
                    raise Conflict()
            for key, data, merge in self.writes:
                self.store.write(key, data, merge)


def transactional(fn):
    def run(transaction):
        while True:
            transaction.attempts += 1
            transaction.reads, transaction.writes = {}, []
            result = fn(transaction)
            try:
                transaction.commit()
                return result
            except Conflict:
                if transaction.attempts >= transaction.max_attempts:
                    raise
    return run


class FakeDB:
    def __init__(self):
        self.store = Store()
        self.on_read = None  # gancho para simular outro cliente escrevendo no meio

    def collection(self, name):
        return Collection(self.store, name)

    def transaction(self, max_attempts=5):
        return Transaction(self.store, max_attempts)

    def batch(self):
        return Batch(self.store)


class FakeFirestore:
    transactional = staticmethod(transactional)
    Increment = Increment


@pytest.fixture
def fb(monkeypatch):
    """Instancia o backend de verdade, trocando só o SDK do Firebase pelo falso."""
    import firebase_admin
    from firebase_admin import credentials, firestore

    db = FakeDB()
    captured = {}
    monkeypatch.setattr(firebase_admin, "get_app", lambda name: (_ for _ in ()).throw(ValueError()))
    monkeypatch.setattr(firebase_admin, "initialize_app", lambda cred, name: ("app", name))
    monkeypatch.setattr(credentials, "Certificate", lambda info: captured.setdefault("info", info))
    monkeypatch.setattr(firestore, "client", lambda app: db)
    monkeypatch.setattr(firestore, "transactional", FakeFirestore.transactional)
    monkeypatch.setattr(firestore, "Increment", Increment)
    monkeypatch.setattr(FB, "CACHE_TTL", 0.0)
    backend = FB.FirebaseBackend({"type": "service_account", "private_key": "-----BEGIN\\nABC\\n-----END"})
    backend._captured = captured
    return backend


def test_private_key_newlines_are_fixed(fb):
    assert fb._captured["info"]["private_key"] == "-----BEGIN\nABC\n-----END"
    assert fb.name == "firebase"


def test_create_get_and_duplicate(fb):
    room, host = R.new_room("FBXYZ", "Ana")
    assert fb.create_room("FBXYZ", room) is True
    assert fb.create_room("FBXYZ", room) is False
    got = fb.get_room("FBXYZ")
    assert got["version"] == 1 and got["players"][0]["token"] == host["token"]
    got["players"].clear()  # cópia: não altera o cache
    assert fb.get_room("FBXYZ")["players"]
    assert fb.get_room("NADA") is None


def test_transact_and_errors(fb):
    room, host = R.new_room("FBXYZ", "Ana")
    fb.create_room("FBXYZ", room)
    state, bia = fb.transact("FBXYZ", lambda r: R.join_room(r, "Bia"))
    assert state["version"] == 2 and fb.get_room("FBXYZ")["version"] == 2
    with pytest.raises(R.RoomError):
        fb.transact("FBXYZ", lambda r: R.join_room(r, "bia"))
    with pytest.raises(NoChange):
        fb.transact("FBXYZ", lambda r: (_ for _ in ()).throw(NoChange()))
    with pytest.raises(RoomNotFound):
        fb.transact("NADA", lambda r: None)
    assert fb.get_room("FBXYZ")["version"] == 2
    # reconexão pelo token
    assert R.player_by_token(fb.get_room("FBXYZ"), bia["token"])["id"] == bia["id"]


def test_transaction_retries_on_conflict(fb):
    room, _ = R.new_room("FBXYZ", "Ana")
    room["counter"] = 0
    fb.create_room("FBXYZ", room)
    calls = {"n": 0}

    def fn(state):
        calls["n"] += 1
        if calls["n"] == 1:  # outro cliente grava no meio da nossa transação
            fb.transact("FBXYZ", lambda s: s.__setitem__("counter", s["counter"] + 100))
        state["counter"] += 1

    state, _ = fb.transact("FBXYZ", fn)
    assert calls["n"] == 2
    assert state["counter"] == 101 and fb.get_room("FBXYZ")["counter"] == 101


def test_concurrent_transactions_with_threads(fb):
    room, _ = R.new_room("FBXYZ", "Ana")
    room["counter"] = 0
    fb.create_room("FBXYZ", room)

    def worker():
        for _ in range(10):
            fb.transact("FBXYZ", lambda s: s.__setitem__("counter", s["counter"] + 1))

    # max_attempts=8 no backend; poucas threads para não estourar as tentativas
    threads = [threading.Thread(target=worker) for _ in range(3)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert fb.get_room("FBXYZ")["counter"] == 30


def test_presence_and_stats(fb):
    fb.heartbeat("FBXYZ", "p1", 10.0)
    fb.heartbeat("FBXYZ", "p2", 12.0)
    fb._cache.clear()
    assert fb.presence("FBXYZ") == {"p1": 10.0, "p2": 12.0}
    fb.record_stats([("ana", "Ana", {"games": 1, "wins": 1, "points": 30, "bogus": 1})])
    fb.record_stats([("ana", "Ana", {"games": 1, "wins": 0, "points": 5}),
                     ("bia", "Bia", {"games": 1, "wins": 2, "points": 1})])
    rows = fb.ranking()
    assert [r["key"] for r in rows] == ["bia", "ana"]
    ana = rows[1]
    assert ana["games"] == 2 and ana["points"] == 35 and "bogus" not in ana


def test_make_backend_picks_firebase_when_secrets_exist(fb, monkeypatch):
    from storage import make_backend

    monkeypatch.delenv("UNO_BACKEND", raising=False)
    be, warn = make_backend({"firebase": {"type": "service_account", "private_key": "x"}})
    assert be.name == "firebase" and warn is None
