"""Fluxo de sala: criar, entrar, limite de 6, nomes repetidos, começar, sair, anfitrião, bots."""

import random

import pytest

from game import engine as E
from game import rooms as R


def make(n_humans=1):
    room, host = R.new_room("ABCDE", "Ana", now=1000.0)
    players = [host]
    for i in range(1, n_humans):
        players.append(R.join_room(room, f"Jogador {i}"))
    return room, players


def test_new_room_and_code_helpers():
    room, host = R.new_room("ABCDE", "  Ana   Maria ")
    assert host["name"] == "Ana Maria" and room["host"] == host["id"]
    assert room["status"] == "lobby" and len(room["players"]) == 1
    code = R.new_code(random.Random(1))
    assert len(code) == R.CODE_LENGTH and all(c in R.CODE_ALPHABET for c in code)
    assert R.normalize_code(" ab-cd e9") == "ABCDE"
    assert R.name_key("João Pé") == "joao-pe"
    with pytest.raises(R.RoomError):
        R.clean_name("   ")
    assert len(R.clean_name("x" * 50)) == R.MAX_NAME


def test_join_and_duplicate_names():
    room, (host,) = make()
    bia = R.join_room(room, "Bia")
    assert bia["token"] != host["token"] and bia["id"] != host["id"]
    with pytest.raises(R.RoomError, match="nome"):
        R.join_room(room, "BIA")
    with pytest.raises(R.RoomError, match="nome"):
        R.join_room(room, " ana ")


def test_max_six_players_including_bots():
    room, (host,) = make()
    R.add_bot(room, host["id"])
    for i in range(4):
        R.join_room(room, f"P{i}")
    assert len(room["players"]) == 6
    with pytest.raises(R.RoomError, match="cheia"):
        R.join_room(room, "Sétimo")
    with pytest.raises(R.RoomError, match="cheia"):
        R.add_bot(room, host["id"])


def test_only_host_adds_bots_removes_and_starts():
    room, (host, other) = make(2)
    for fn in (lambda: R.add_bot(room, other["id"]),
               lambda: R.start_game(room, other["id"]),
               lambda: R.remove_player(room, other["id"], host["id"]),
               lambda: R.set_target(room, other["id"], 100)):
        with pytest.raises(R.RoomError, match="anfitrião"):
            fn()
    bot = R.add_bot(room, host["id"])
    assert bot["bot"] and bot["name"].startswith("Bot")
    R.remove_player(room, host["id"], bot["id"])
    assert bot not in room["players"]
    with pytest.raises(R.RoomError):
        R.remove_player(room, host["id"], host["id"])
    with pytest.raises(R.RoomError):
        R.set_target(room, host["id"], 123)


def test_start_requires_two_players():
    room, (host,) = make()
    with pytest.raises(R.RoomError):
        R.start_game(room, host["id"])
    R.add_bot(room, host["id"])
    R.set_target(room, host["id"], 200)
    R.start_game(room, host["id"], rng=random.Random(1))
    assert room["status"] == "playing"
    assert room["game"]["target"] == 200 and room["game"]["gid"]
    assert E.total_cards(room["game"]) == 108
    with pytest.raises(R.RoomError, match="começou"):
        R.join_room(room, "Atrasado")
    with pytest.raises(R.RoomError):
        R.start_game(room, host["id"])


def test_leave_in_lobby_frees_seat_and_transfers_host():
    room, (host, bia) = make(2)
    R.leave_room(room, host["id"])
    assert room["host"] == bia["id"]
    assert [p["id"] for p in room["players"]] == [bia["id"]]
    R.leave_room(room, "inexistente")  # não quebra


def test_leave_during_game_bot_takes_over_and_host_transfers():
    room, (host, bia) = make(2)
    R.start_game(room, host["id"], rng=random.Random(2))
    R.leave_room(room, host["id"])
    p = R.find_player(room, host["id"])
    assert p["autopilot"] and p["left"]
    assert room["host"] == bia["id"]
    assert R.automated(p)


def test_act_validates_turn_and_unknown_action():
    room, (host, bia) = make(2)
    R.start_game(room, host["id"], rng=random.Random(5))
    game = room["game"]
    waiting = next(pid for pid in game["players"] if pid != E.whose_action(game))
    with pytest.raises(E.GameError):
        R.act(room, waiting, "draw")
    with pytest.raises(R.RoomError):
        R.act(room, host["id"], "dançar")
    with pytest.raises(R.RoomError):
        R.act(room, "intruso", "draw")


def test_bot_due_respects_delay_and_runs(monkeypatch):
    room, (host,) = make()
    bot = R.add_bot(room, host["id"])
    R.start_game(room, host["id"], rng=random.Random(3), now=1000.0)
    game = room["game"]
    # força a vez do bot
    game["pending"] = None
    game["current"] = game["players"].index(bot["id"])
    assert R.bot_due(room, now=1000.0 + R.BOT_DELAY / 2) is None
    assert R.bot_due(room, now=1000.0 + R.BOT_DELAY + 0.1) == bot["id"]
    seq = game["seq"]
    assert R.run_bot(room, bot["id"], rng=random.Random(1), now=1000.0 + R.BOT_DELAY + 0.1)
    assert game["seq"] > seq
    assert not R.run_bot(room, bot["id"], now=1000.0 + R.BOT_DELAY + 0.2)  # atraso de novo


def test_host_skip_and_autopilot_for_offline_player():
    room, (host, bia) = make(2)
    R.start_game(room, host["id"], rng=random.Random(4))
    game = room["game"]
    game["pending"] = None
    game["current"] = game["players"].index(bia["id"])
    with pytest.raises(R.RoomError):
        R.host_skip(room, bia["id"], bia["id"])
    R.host_skip(room, host["id"], bia["id"])
    assert E.current_player(game) == host["id"]
    R.host_autopilot(room, host["id"], bia["id"], True)
    assert R.find_player(room, bia["id"])["autopilot"]
    # quando ela age de novo, retoma o controle
    assert R.resume_control(room, bia["id"]) is True
    assert not R.find_player(room, bia["id"])["autopilot"]
    assert R.resume_control(room, bia["id"]) is False


def test_auto_takeover_after_long_absence():
    room, (host, bia) = make(2)
    R.start_game(room, host["id"], rng=random.Random(4), now=1000.0)
    game = room["game"]
    game["pending"] = None
    game["current"] = game["players"].index(bia["id"])
    presence = {host["id"]: 1000.0 + 500, bia["id"]: 1000.0}
    assert R.auto_takeover(room, presence, now=1000.0 + 10) is None
    assert R.auto_takeover(room, presence, now=1000.0 + R.AUTO_TAKEOVER + 5) == bia["id"]
    assert R.find_player(room, bia["id"])["autopilot"]


def test_full_room_game_with_bots_and_back_to_lobby():
    room, (host,) = make()
    for _ in range(3):
        R.add_bot(room, host["id"])
    for p in room["players"]:
        if not p["bot"]:
            p["autopilot"] = True  # o humano também vira bot para a simulação
    rng = random.Random(9)
    R.start_game(room, host["id"], rng=rng, now=0.0)
    t = 0.0
    for _ in range(5000):
        if room["game"]["status"] != "playing":
            break
        t += R.BOT_DELAY + 0.01
        pid = R.bot_due(room, now=t)
        assert pid
        R.run_bot(room, pid, rng=rng, now=t)
    assert room["game"]["status"] == "game_over"
    assert room["stats_pending"] and room["games_played"] == 1
    entries = R.stats_entries(room)
    assert [e[1] for e in entries] == ["Ana"]  # bots não entram no ranking
    inc = entries[0][2]
    assert inc["games"] == 1 and inc["wins"] in (0, 1)
    R.back_to_lobby(room, host["id"])
    assert room["status"] == "lobby" and room["game"] is None and room["last_game"]


def test_next_round_only_host_and_only_after_round():
    room, (host, bia) = make(2)
    R.set_target(room, host["id"], 500)
    R.start_game(room, host["id"], rng=random.Random(1))
    with pytest.raises(E.GameError):
        R.next_round(room, host["id"])
    with pytest.raises(R.RoomError):
        R.back_to_lobby(room, host["id"])
    room["game"]["status"] = "round_over"
    with pytest.raises(R.RoomError):
        R.next_round(room, bia["id"])
    R.next_round(room, host["id"], rng=random.Random(2))
    assert room["game"]["round"] == 2
