"""LocalBackend: CRUD, transações, conflitos de versão, escrita concorrente e reconexão."""

import multiprocessing
import threading

import pytest

from game import rooms as R
from storage import LocalBackend, NoChange, RoomNotFound, make_backend
from storage.base import STAT_FIELDS


@pytest.fixture
def be(tmp_path):
    return LocalBackend(tmp_path / "data")


def test_create_get_and_duplicate(be):
    room, host = R.new_room("ABCDE", "Ana")
    assert be.create_room("ABCDE", room) is True
    assert be.create_room("ABCDE", room) is False
    got = be.get_room("ABCDE")
    assert got["code"] == "ABCDE" and got["version"] == 1
    assert got["players"][0]["token"] == host["token"]
    assert be.get_room("ZZZZZ") is None


def test_transact_increments_version_and_returns_result(be):
    room, host = R.new_room("ABCDE", "Ana")
    be.create_room("ABCDE", room)
    state, player = be.transact("ABCDE", lambda r: R.join_room(r, "Bia"))
    assert state["version"] == 2 and player["name"] == "Bia"
    assert be.get_room("ABCDE")["version"] == 2
    assert len(be.get_room("ABCDE")["players"]) == 2


def test_failed_transaction_writes_nothing(be):
    room, _ = R.new_room("ABCDE", "Ana")
    be.create_room("ABCDE", room)
    with pytest.raises(R.RoomError):
        be.transact("ABCDE", lambda r: R.join_room(r, "ana"))  # nome repetido
    with pytest.raises(NoChange):
        be.transact("ABCDE", lambda r: (_ for _ in ()).throw(NoChange()))
    assert be.get_room("ABCDE")["version"] == 1


def test_transact_missing_room(be):
    with pytest.raises(RoomNotFound):
        be.transact("NOPE", lambda r: None)


def test_optimistic_version_conflict_is_detected_by_caller(be):
    """Dois clientes leram a versão 1; o segundo percebe que o estado mudou."""
    room, _ = R.new_room("ABCDE", "Ana")
    be.create_room("ABCDE", room)
    seen_by_a = be.get_room("ABCDE")["version"]
    seen_by_b = be.get_room("ABCDE")["version"]

    def guarded(expected):
        def fn(state):
            if state["version"] != expected:
                raise NoChange()
            state["marker"] = expected
        return fn

    be.transact("ABCDE", guarded(seen_by_a))
    with pytest.raises(NoChange):
        be.transact("ABCDE", guarded(seen_by_b))
    assert be.get_room("ABCDE")["version"] == 2


def test_concurrent_writes_with_threads_lose_nothing(be):
    room, _ = R.new_room("ABCDE", "Ana")
    room["counter"] = 0
    be.create_room("ABCDE", room)
    n_threads, per_thread = 8, 25

    def inc(state):
        state["counter"] += 1

    def worker():
        for _ in range(per_thread):
            be.transact("ABCDE", inc)

    threads = [threading.Thread(target=worker) for _ in range(n_threads)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    final = be.get_room("ABCDE")
    assert final["counter"] == n_threads * per_thread
    assert final["version"] == 1 + n_threads * per_thread


def _proc_worker(root, count):
    from storage import LocalBackend as LB

    b = LB(root)
    for _ in range(count):
        b.transact("PROCS", lambda s: s.__setitem__("counter", s["counter"] + 1))


def test_concurrent_writes_with_processes(be):
    """Vários processos (como vários servidores na mesma máquina) também não se atropelam."""
    room, _ = R.new_room("PROCS", "Ana")
    room["counter"] = 0
    be.create_room("PROCS", room)
    ctx = multiprocessing.get_context("spawn")
    procs = [ctx.Process(target=_proc_worker, args=(str(be.root), 15)) for _ in range(4)]
    for p in procs:
        p.start()
    for p in procs:
        p.join(60)
    assert all(p.exitcode == 0 for p in procs)
    assert be.get_room("PROCS")["counter"] == 60


def test_concurrent_joins_respect_capacity(be):
    room, _ = R.new_room("ABCDE", "Host")
    be.create_room("ABCDE", room)
    results = []

    def join(i):
        try:
            be.transact("ABCDE", lambda r: R.join_room(r, f"J{i}"))
            results.append(True)
        except R.RoomError:
            results.append(False)

    threads = [threading.Thread(target=join, args=(i,)) for i in range(12)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert results.count(True) == 5
    assert len(be.get_room("ABCDE")["players"]) == 6


def test_reconnection_by_token_returns_same_seat_and_hand(be):
    room, host = R.new_room("ABCDE", "Ana")
    be.create_room("ABCDE", room)
    _, bia = be.transact("ABCDE", lambda r: R.join_room(r, "Bia"))
    be.transact("ABCDE", lambda r: R.start_game(r, host["id"]))
    hand_before = be.get_room("ABCDE")["game"]["hands"][bia["id"]]
    # "outra aba": um backend novo lendo a mesma pasta
    other = LocalBackend(be.root)
    again = R.player_by_token(other.get_room("ABCDE"), bia["token"])
    assert again["id"] == bia["id"] and again["name"] == "Bia"
    assert other.get_room("ABCDE")["game"]["hands"][again["id"]] == hand_before
    assert R.player_by_token(other.get_room("ABCDE"), "token-falso") is None
    assert R.player_by_token(other.get_room("ABCDE"), "") is None


def test_presence_heartbeat(be):
    be.heartbeat("ABCDE", "p1", 100.0)
    be.heartbeat("ABCDE", "p2", 105.0)
    be.heartbeat("ABCDE", "p1", 110.0)
    assert be.presence("ABCDE") == {"p1": 110.0, "p2": 105.0}
    assert be.presence("OTHER") == {}
    assert R.is_offline(be.presence("ABCDE"), "p2", now=105.0 + R.OFFLINE_AFTER + 1)
    assert not R.is_offline(be.presence("ABCDE"), "p1", now=112.0)


def test_stats_accumulate_and_rank(be):
    be.record_stats([("ana", "Ana", {"games": 1, "wins": 1, "points": 50, "uno_shouts": 2, "bogus": 9})])
    be.record_stats([("ana", "Ana", {"games": 1, "wins": 0, "points": 10}),
                     ("bia", "Bia", {"games": 1, "wins": 1, "points": 99})])
    rows = be.ranking()
    ana = next(r for r in rows if r["key"] == "ana")
    assert ana["games"] == 2 and ana["wins"] == 1 and ana["points"] == 60 and ana["uno_shouts"] == 2
    assert "bogus" not in ana
    assert [r["key"] for r in rows] == ["bia", "ana"]  # mesmo nº de vitórias: desempata por pontos
    assert set(STAT_FIELDS) <= set(ana)


def test_cleanup_removes_old_rooms(be):
    import os
    import time

    room, _ = R.new_room("OLDXX", "Ana")
    be.create_room("OLDXX", room)
    old = time.time() - 72 * 3600
    os.utime(be._room_path("OLDXX"), (old, old))
    room2, _ = R.new_room("NEWXX", "Ana")
    be.create_room("NEWXX", room2)
    assert be.cleanup(48) == 1
    assert be.get_room("OLDXX") is None and be.get_room("NEWXX") is not None


def test_make_backend_defaults_to_local(data_dir, monkeypatch):
    monkeypatch.delenv("UNO_BACKEND")
    be, warn = make_backend({})
    assert be.name == "local" and warn is None
    be, warn = make_backend(None)
    assert be.name == "local"


def test_make_backend_falls_back_when_firebase_credentials_are_bad(data_dir, monkeypatch):
    monkeypatch.delenv("UNO_BACKEND")
    be, warn = make_backend({"firebase": {"type": "service_account", "project_id": "x"}})
    assert be.name == "local"
    assert warn and "Firebase" in warn


def test_make_backend_forced_local(data_dir):
    be, warn = make_backend({"firebase": {"project_id": "x"}})
    assert be.name == "local" and warn is None
