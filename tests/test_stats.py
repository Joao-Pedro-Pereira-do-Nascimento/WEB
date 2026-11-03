"""Estatísticas por jogador: coletadas no motor e acumuladas no armazenamento."""

import random

from game import bots as B
from game import engine as E
from game import rooms as R
from storage import LocalBackend
from conftest import card, setup_game


def test_engine_counts_plays_draws_and_shouts():
    a1 = card("red", value=2)
    g = setup_game({"a": [a1, card("red", "skip")], "b": [card("blue", value=1)]}, card("red", value=1),
                   deck=[card("green", value=5)] * 5)
    E.shout_uno(g, "a")
    E.play_card(g, "a", a1["id"])
    E.draw_action(g, "b")
    s = g["stats"]
    assert s["a"]["cards_played"] == 1 and s["a"]["uno_shouts"] == 1
    assert s["b"]["cards_drawn"] == 1


def test_simulated_stats_are_consistent():
    g = B.simulate_game(4, 11)
    played = sum(st["cards_played"] for st in g["stats"].values())
    assert played > 0
    assert all(st["wild4_played"] <= st["action_played"] <= st["cards_played"] for st in g["stats"].values())


def test_stats_flow_room_to_ranking(tmp_path):
    be = LocalBackend(tmp_path)
    for game_no in range(2):
        room, host = R.new_room("ABCDE", "Ana")
        R.add_bot(room, host["id"])
        R.start_game(room, host["id"], rng=random.Random(game_no))
        room["players"][0]["autopilot"] = True
        rng, t = random.Random(game_no), 0.0
        while room["game"]["status"] == "playing":
            t += 10
            R.run_bot(room, R.bot_due(room, now=t), rng=rng, now=t)
        be.record_stats(R.stats_entries(room))
    rows = be.ranking()
    assert len(rows) == 1 and rows[0]["name"] == "Ana" and rows[0]["games"] == 2
    assert rows[0]["cards_played"] > 0
