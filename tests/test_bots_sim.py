"""Simulações completas só com bots: sempre terminam e nunca perdem/criam cartas."""

import random

import pytest

from game import bots as B
from game import engine as E


def _check(game):
    assert E.total_cards(game) == 108
    ids = [c["id"] for c in game["deck"] + game["discard"]] + [c["id"] for h in game["hands"].values() for c in h]
    assert len(set(ids)) == 108


@pytest.mark.parametrize("n_players", [2, 3, 4, 5, 6])
@pytest.mark.parametrize("seed", range(40))
def test_single_round_games_terminate_and_conserve_cards(n_players, seed):
    game = B.simulate_game(n_players, seed)
    assert game["status"] == "game_over"
    assert game["winner"] in game["players"]
    assert game["hands"][game["winner"]] == []
    _check(game)


@pytest.mark.parametrize("n_players", [2, 4, 6])
@pytest.mark.parametrize("seed", range(5))
def test_multi_round_games_reach_target(n_players, seed):
    game = B.simulate_game(n_players, 1000 + seed, target=200)
    assert game["scores"][game["winner"]] >= 200
    _check(game)


@pytest.mark.parametrize("seed", range(30))
def test_card_count_conserved_after_every_step(seed):
    rng = random.Random(seed)
    n = 2 + seed % 5
    pids = [f"b{i}" for i in range(n)]
    game = E.new_game(pids, rng=rng)
    for _ in range(20000):
        if game["status"] != "playing":
            break
        B.bot_step(game, E.whose_action(game), rng)
        assert E.total_cards(game) == 108
        assert game["current"] in range(n)
    assert game["status"] == "game_over"


def test_bot_step_ignores_when_not_its_turn():
    game = E.new_game(["a", "b"], rng=random.Random(1))
    other = next(p for p in game["players"] if p != E.whose_action(game))
    assert B.bot_step(game, other) == "idle"


def test_events_are_capped_and_sequential():
    game = B.simulate_game(4, 7)
    seqs = [ev["seq"] for ev in game["events"]]
    assert seqs == sorted(seqs) and len(seqs) <= E.MAX_EVENTS
