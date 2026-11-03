"""RTDBBackend (Firebase Realtime Database) testado com um banco falso em memória.

O falso imita o necessário de ``firebase_admin.db``: ``reference(path, app=)``,
``get``/``set``/``delete`` e ``transaction`` com ETag (lê, roda a função,
só grava se ninguém escreveu no meio; senão repete). Também recusa chaves
proibidas pelo RTDB, para provar que o backend as escapa. Sem rede.
"""

import copy
import json
import threading

import pytest

from game import engine as E
from game import rooms as R
from storage import NoChange, RoomNotFound, make_backend
from storage import rtdb as RT

BAD = set(".$#[]")


class Aborted(Exception):
    pass


class FakeRTDB:
    def __init__(self):
        self.tree = {}
        self.etags = {}           # caminho -> nº de escritas (ETag)
        self.lock = threading.RLock()
        self.on_transaction_read = None  # gancho: outro cliente escreve no meio
        self.tx_calls = 0

    # ---- navegação
    @staticmethod
    def split(path):
        parts = [p for p in path.split("/") if p]
        for p in parts:
            if BAD & set(p):
                raise ValueError(f"chave inválida no RTDB: {p!r}")
        return parts

    def _get(self, parts):
        node = self.tree
        for p in parts:
            if not isinstance(node, dict) or p not in node:
                return None
            node = node[p]
        return copy.deepcopy(node)

    def _set(self, parts, value):
        value = copy.deepcopy(value)
        if value is not None:
            json.dumps(value)  # só tipos JSON
        node = self.tree
        for p in parts[:-1]:
            node = node.setdefault(p, {})
        if value is None or value == {} or value == []:   # RTDB descarta vazios
            node.pop(parts[-1], None)
        else:
            node[parts[-1]] = value
        # qualquer escrita muda a ETag do caminho e dos ancestrais/descendentes
        key = "/".join(parts)
        for k in list(self.etags) + [key]:
            if k.startswith(key) or key.startswith(k):
                self.etags[k] = self.etags.get(k, 0) + 1

    def reference(self, path="/", app=None):
        assert app == "fake-app"
        return Ref(self, path)


class Ref:
    def __init__(self, db, path):
        self.db, self.parts = db, FakeRTDB.split(path)
        self.key_path = "/".join(self.parts)

    def child(self, name):
        return Ref(self.db, self.key_path + "/" + name)

    def get(self, etag=False, shallow=False):
        with self.db.lock:
            self.db.etags.setdefault(self.key_path, 0)
            val = self.db._get(self.parts)
            if shallow and isinstance(val, dict):
                val = {k: True for k in val}
            if etag:
                return val, self.db.etags.get(self.key_path, 0)
            return val

    def set(self, value):
        with self.db.lock:
            self.db._set(self.parts, value)

    def delete(self):
        with self.db.lock:
            self.db._set(self.parts, None)

    def transaction(self, update):
        self.db.tx_calls += 1
        data, tag = self.get(etag=True)
        for _ in range(25):
            if self.db.on_transaction_read:
                hook, self.db.on_transaction_read = self.db.on_transaction_read, None
                hook()
            new = update(data)       # exceções propagam (como no SDK)
            with self.db.lock:
                if self.db.etags.get(self.key_path, 0) == tag:
                    self.db._set(self.parts, new)
                    return new
                data, tag = self.db._get(self.parts), self.db.etags.get(self.key_path, 0)
        raise Aborted()


@pytest.fixture
def fake():
    return FakeRTDB()


@pytest.fixture
def rt(fake, monkeypatch):
    monkeypatch.setattr(RT, "CACHE_TTL", 0.0)
    be = RT.RTDBBackend(None, "https://exemplo-default-rtdb.firebaseio.com", db_module=fake, app="fake-app")
    return be


def test_safe_key_escapes_forbidden_chars():
    assert RT.safe_key("a.b$c#d[e]f/g") == "a%2Eb%24c%23d%5Be%5Df%2Fg"
    assert RT.safe_key("ana") == "ana"
    assert RT.safe_key("") == "_"
    assert RT.safe_key("100%") == "100%25"


def test_create_get_duplicate_and_state_is_json_string(rt, fake):
    room, host = R.new_room("RTDBX", "Ana")
    assert rt.create_room("RTDBX", room) is True
    assert rt.create_room("RTDBX", room) is False
    raw = fake.tree["uno"]["rooms"]["RTDBX"]
    assert isinstance(raw["data"], str) and raw["version"] == 1
    got = rt.get_room("RTDBX")
    assert got["players"][0]["token"] == host["token"]
    assert got["lobby_log"] and got["game"] is None  # None e listas preservados pelo JSON
    got["players"].clear()
    assert rt.get_room("RTDBX")["players"]
    assert rt.get_room("NADAX") is None


def test_transact_errors_write_nothing(rt):
    room, host = R.new_room("RTDBX", "Ana")
    rt.create_room("RTDBX", room)
    state, bia = rt.transact("RTDBX", lambda r: R.join_room(r, "Bia"))
    assert state["version"] == 2 and rt.get_room("RTDBX")["version"] == 2
    with pytest.raises(R.RoomError):
        rt.transact("RTDBX", lambda r: R.join_room(r, "bia"))
    with pytest.raises(NoChange):
        rt.transact("RTDBX", lambda r: (_ for _ in ()).throw(NoChange()))
    with pytest.raises(RoomNotFound):
        rt.transact("NADAX", lambda r: None)
    assert rt.get_room("RTDBX")["version"] == 2
    assert R.player_by_token(rt.get_room("RTDBX"), bia["token"])["id"] == bia["id"]


def test_transaction_retries_when_someone_writes_in_between(rt, fake):
    room, _ = R.new_room("RTDBX", "Ana")
    room["counter"] = 0
    rt.create_room("RTDBX", room)
    calls = {"n": 0}

    def other_client():
        rt.transact("RTDBX", lambda s: s.__setitem__("counter", s["counter"] + 100))

    fake.on_transaction_read = other_client

    def fn(state):
        calls["n"] += 1
        state["counter"] += 1

    state, _ = rt.transact("RTDBX", fn)
    assert calls["n"] == 2  # rodou de novo com o estado novo
    assert state["counter"] == 101 and rt.get_room("RTDBX")["counter"] == 101


def test_concurrent_plays_only_first_wins(rt, fake):
    """Dois clientes tentam jogar na mesma vez: o motor recusa o segundo."""
    import random

    room, host = R.new_room("RTDBX", "Ana")
    R.join_room(room, "Bia")
    R.start_game(room, host["id"], rng=random.Random(3))
    rt.create_room("RTDBX", room)
    g = rt.get_room("RTDBX")["game"]
    actor = E.whose_action(g)
    fake.on_transaction_read = lambda: rt.transact("RTDBX", lambda r: R.act(r, actor, "draw"))
    with pytest.raises(E.GameError):
        rt.transact("RTDBX", lambda r: R.act(r, actor, "draw"))
    g2 = rt.get_room("RTDBX")["game"]
    assert E.whose_action(g2) != actor or g2.get("pending")
    assert E.total_cards(g2) == 108


def test_concurrent_threads_lose_nothing(rt):
    room, _ = R.new_room("RTDBX", "Ana")
    room["counter"] = 0
    rt.create_room("RTDBX", room)

    def worker():
        for _ in range(15):
            rt.transact("RTDBX", lambda s: s.__setitem__("counter", s["counter"] + 1))

    threads = [threading.Thread(target=worker) for _ in range(4)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert rt.get_room("RTDBX")["counter"] == 60


def test_presence_stats_and_weird_names(rt, fake):
    rt.heartbeat("RTDBX", "p1", 10.0)
    rt.heartbeat("RTDBX", "p2", 12.0)
    rt._cache.clear()
    assert rt.presence("RTDBX") == {"p1": 10.0, "p2": 12.0}
    rt.record_stats([("ana", "Ana", {"games": 1, "wins": 1, "points": 30, "bogus": 1})])
    rt.record_stats([("ana", "Ana", {"games": 1, "wins": 0, "points": 5}),
                     ("j.r$#[x]", "J.R. [x]", {"games": 1, "wins": 2, "points": 1})])
    rows = rt.ranking()
    assert [r["name"] for r in rows] == ["J.R. [x]", "Ana"]
    ana = rows[1]
    assert ana["games"] == 2 and ana["points"] == 35 and "bogus" not in ana


def test_delete_room_and_cleanup(rt, fake):
    import time

    room, _ = R.new_room("OLDXX", "Ana")
    rt.create_room("OLDXX", room)
    rt.create_room("NEWXX", R.new_room("NEWXX", "Bia")[0])
    fake.tree["uno"]["rooms"]["OLDXX"]["updated_at"] = time.time() - 72 * 3600
    rt.heartbeat("OLDXX", "p1", 1.0)
    assert rt.cleanup(48) == 1
    assert rt.get_room("OLDXX") is None and rt.get_room("NEWXX") is not None
    assert "OLDXX" not in fake.tree["uno"].get("presence", {})


def test_make_backend_selects_rtdb_with_database_url(monkeypatch, fake, data_dir):
    import firebase_admin
    from firebase_admin import credentials, db

    monkeypatch.delenv("UNO_BACKEND", raising=False)
    seen = {}
    monkeypatch.setattr(firebase_admin, "get_app", lambda name: (_ for _ in ()).throw(ValueError()))

    def init(cred, options, name):
        seen["options"], seen["name"] = options, name
        return "fake-app"

    monkeypatch.setattr(firebase_admin, "initialize_app", init)
    monkeypatch.setattr(credentials, "Certificate", lambda info: seen.setdefault("info", info))
    monkeypatch.setattr(db, "reference", fake.reference)
    url = "https://baralhoflocloriobr-default-rtdb.firebaseio.com"
    be, warn = make_backend({"firebase": {"type": "service_account", "private_key": "A\\nB", "database_url": url}})
    assert be.name == "rtdb" and warn is None
    assert seen["options"] == {"databaseURL": url}
    assert "database_url" not in seen["info"] and seen["info"]["private_key"] == "A\nB"
    room, _ = R.new_room("MKBEX", "Ana")
    assert be.create_room("MKBEX", room)


def test_make_backend_rtdb_bad_credentials_falls_back(monkeypatch, data_dir):
    monkeypatch.delenv("UNO_BACKEND", raising=False)
    be, warn = make_backend({"firebase": {"type": "service_account", "project_id": "x",
                                          "database_url": "https://x-default-rtdb.firebaseio.com"}})
    assert be.name == "local" and "Realtime Database" in warn


def test_secrets_example_has_database_url():
    from conftest import ROOT

    text = (ROOT / ".streamlit" / "secrets.toml.example").read_text(encoding="utf-8")
    assert 'database_url = "https://baralhoflocloriobr-default-rtdb.firebaseio.com"' in text
    gitignore = (ROOT / ".gitignore").read_text(encoding="utf-8")
    assert ".streamlit/secrets.toml" in gitignore


# --------------------------------------------------------------------------- ranking global

def test_stats_concurrent_increments_lose_nothing(rt):
    def worker():
        for _ in range(10):
            rt.record_stats([("ana", "Ana", {"games": 1, "wins": 1, "points": 2})])

    threads = [threading.Thread(target=worker) for _ in range(4)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    rt._cache.clear()
    row = rt.ranking()[0]
    assert row["games"] == 40 and row["wins"] == 40 and row["points"] == 80


def test_stats_are_idempotent_per_game(rt, fake):
    entries = [("ana", "Ana", {"games": 1, "wins": 1})]
    rt.record_stats(entries, game_id="SALAX-abc123")
    rt.record_stats(entries, game_id="SALAX-abc123")      # mesmo jogo de novo: ignorado
    rt.record_stats(entries, game_id="SALAX-def456")
    rt._cache.clear()
    assert rt.ranking()[0]["games"] == 2
    assert set(fake.tree["uno"]["stats_games"]) == {"SALAX-abc123", "SALAX-def456"}


def test_full_game_stats_exclude_bots_and_escape_names(rt, fake):
    import random

    from game import bots as B

    room, host = R.new_room("RANKX", "J.R. $ilva [#1]")
    R.add_bot(room, host["id"])
    R.start_game(room, host["id"], rng=random.Random(5))
    rng = random.Random(9)
    for _ in range(5000):
        g = room["game"]
        if g["status"] != "playing":
            break
        pid = E.whose_action(g)
        B.bot_step(g, pid, rng)
        R._after(room, "playing")
    assert room["stats_pending"]
    entries = R.stats_entries(room)
    assert [name for _, name, _ in entries] == ["J.R. $ilva [#1]"]   # bot fora
    rt.record_stats(entries, game_id=f"RANKX-{room['game']['gid']}")
    rt._cache.clear()
    rows = rt.ranking()
    assert len(rows) == 1 and rows[0]["name"] == "J.R. $ilva [#1]" and rows[0]["games"] == 1
    key = rows[0]["key"]
    assert not (set(key) & BAD) and key == R.name_key("J.R. $ilva [#1]")


def test_avatar_swap_persisted_in_rtdb(rt):
    room, host = R.new_room("AVATR", "Ana", avatar="saci")
    bia = R.join_room(room, "Bia", "iara")
    rt.create_room("AVATR", room)
    rt.transact("AVATR", lambda r: R.set_avatar(r, bia["id"], "cuca"))
    assert R.find_player(rt.get_room("AVATR"), bia["id"])["avatar"] == "cuca"
    with pytest.raises(R.RoomError):
        rt.transact("AVATR", lambda r: R.set_avatar(r, host["id"], "cuca"))
