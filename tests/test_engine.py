"""Regras do UNO: baralho, jogadas legais, cartas de ação, compra, UNO!, pontuação."""

import random
from collections import Counter

import pytest

from game import engine as E
from conftest import card, setup_game


# --------------------------------------------------------------- baralho

def test_deck_has_108_cards_with_official_composition():
    deck = E.build_deck()
    assert len(deck) == 108
    assert len({c["id"] for c in deck}) == 108
    by_kind = Counter(c["kind"] for c in deck)
    assert by_kind == {"number": 76, "skip": 8, "reverse": 8, "draw2": 8, "wild": 4, "wild4": 4}
    for color in E.COLORS:
        nums = Counter(c["value"] for c in deck if c["color"] == color and c["kind"] == "number")
        assert nums[0] == 1
        assert all(nums[v] == 2 for v in range(1, 10))
        assert sum(1 for c in deck if c["color"] == color) == 25
    assert all(c["color"] == "wild" for c in deck if c["kind"] in E.WILD_KINDS)


def test_card_points():
    assert E.card_points(card("red", value=7)) == 7
    assert E.card_points(card("red", "skip")) == 20
    assert E.card_points(card("red", "reverse")) == 20
    assert E.card_points(card("red", "draw2")) == 20
    assert E.card_points(card("wild", "wild")) == 50
    assert E.card_points(card("wild", "wild4")) == 50
    assert sum(E.card_points(c) for c in E.build_deck()) == 4 * (2 * 45 + 6 * 20) + 8 * 50


# --------------------------------------------------------------- distribuição

@pytest.mark.parametrize("n", [2, 3, 4, 5, 6])
def test_new_game_deals_seven_each_and_conserves_cards(n):
    g = E.new_game([f"p{i}" for i in range(n)], rng=random.Random(n))
    hands = [len(h) for h in g["hands"].values()]
    # o +2 virado no início pode dar 2 cartas a mais para o primeiro
    assert sorted(hands)[:-1] == [7] * (n - 1)
    assert sorted(hands)[-1] in (7, 9)
    assert E.total_cards(g) == 108
    assert g["discard"][0]["kind"] != "wild4"


def test_player_count_limits():
    with pytest.raises(E.GameError):
        E.new_game(["a"])
    with pytest.raises(E.GameError):
        E.new_game([f"p{i}" for i in range(7)])
    with pytest.raises(E.GameError):
        E.new_game(["a", "a"])


def test_first_card_is_never_wild4():
    for seed in range(200):
        g = E.new_game(["a", "b"], rng=random.Random(seed))
        assert g["discard"][0]["kind"] != "wild4"


def test_first_card_wild_requires_color_choice():
    for seed in range(500):
        g = E.new_game(["a", "b", "c"], rng=random.Random(seed))
        if g["discard"][0]["kind"] == "wild":
            break
    else:
        pytest.skip("nenhuma semente virou coringa")
    first = E.current_player(g)
    assert g["pending"] == {"type": "choose_color", "player": first}
    assert E.whose_action(g) == first
    with pytest.raises(E.GameError):
        E.play_card(g, first, g["hands"][first][0]["id"], "red")
    E.choose_start_color(g, first, "blue")
    assert g["color"] == "blue" and g["pending"] is None


# --------------------------------------------------------------- legalidade

def test_matches_color_number_symbol_and_wild():
    top = card("red", value=5)
    assert E.matches(card("red", value=9), top, "red")
    assert E.matches(card("blue", value=5), top, "red")
    assert not E.matches(card("blue", value=6), top, "red")
    assert E.matches(card("wild", "wild"), top, "red")
    assert E.matches(card("wild", "wild4"), top, "red")
    skip = card("green", "skip")
    assert E.matches(card("blue", "skip"), skip, "green")
    assert not E.matches(card("blue", "reverse"), skip, "green")
    # depois de um coringa, vale a cor escolhida
    wild = card("wild", "wild")
    assert E.matches(card("yellow", value=1), wild, "yellow")
    assert not E.matches(card("red", value=1), wild, "yellow")


def test_only_current_player_may_play():
    a1, b1 = card("red", value=3), card("red", value=4)
    g = setup_game({"a": [a1, card("blue", value=1)], "b": [b1, card("blue", value=2)]}, card("red", value=1))
    with pytest.raises(E.GameError, match="vez"):
        E.play_card(g, "b", b1["id"])
    E.play_card(g, "a", a1["id"])
    assert E.current_player(g) == "b"


def test_illegal_card_is_rejected_and_state_unchanged():
    bad = card("blue", value=7)
    g = setup_game({"a": [bad, card("green", value=1)], "b": [card("red", value=2)]}, card("red", value=1))
    with pytest.raises(E.GameError):
        E.play_card(g, "a", bad["id"])
    assert bad in g["hands"]["a"] and len(g["discard"]) == 1 and E.current_player(g) == "a"


def test_cannot_play_card_not_in_hand():
    g = setup_game({"a": [card("red", value=2)], "b": [card("red", value=3)]}, card("red", value=1))
    with pytest.raises(E.GameError):
        E.play_card(g, "a", "não-existe")


def test_wild_needs_color():
    w = card("wild", "wild")
    g = setup_game({"a": [w, card("blue", value=1)], "b": [card("red", value=2)]}, card("red", value=1))
    with pytest.raises(E.GameError):
        E.play_card(g, "a", w["id"])
    with pytest.raises(E.GameError):
        E.play_card(g, "a", w["id"], "purple")
    E.play_card(g, "a", w["id"], "green")
    assert g["color"] == "green" and E.current_player(g) == "b"


def test_playable_cards_lists_only_legal_for_current_player():
    ok, ok2, bad = card("red", value=9), card("wild", "wild"), card("blue", value=2)
    g = setup_game({"a": [ok, ok2, bad], "b": [card("red", value=3)]}, card("red", value=1))
    assert {c["id"] for c in E.playable_cards(g, "a")} == {ok["id"], ok2["id"]}
    assert E.playable_cards(g, "b") == []


# --------------------------------------------------------------- cartas de ação

def three(top, **hands):
    base = {"a": [card("red", value=2), card("red", value=3)],
            "b": [card("blue", value=2), card("blue", value=3)],
            "c": [card("green", value=2), card("green", value=3)]}
    base.update(hands)
    return setup_game(base, top)


def test_skip_jumps_next_player():
    s = card("red", "skip")
    g = three(card("red", value=1), a=[s, card("red", value=4)])
    E.play_card(g, "a", s["id"])
    assert E.current_player(g) == "c"
    assert any(ev["type"] == "skip" and ev["target"] == "b" for ev in g["events"])


def test_reverse_changes_direction_with_three_players():
    r = card("red", "reverse")
    g = three(card("red", value=1), a=[r, card("red", value=4)])
    E.play_card(g, "a", r["id"])
    assert g["direction"] == -1
    assert E.current_player(g) == "c"


def test_reverse_acts_as_skip_with_two_players():
    r = card("red", "reverse")
    g = setup_game({"a": [r, card("red", value=4)], "b": [card("blue", value=1)]}, card("red", value=1))
    E.play_card(g, "a", r["id"])
    assert E.current_player(g) == "a"


def test_skip_with_two_players_plays_again():
    s = card("red", "skip")
    g = setup_game({"a": [s, card("red", value=4)], "b": [card("blue", value=1)]}, card("red", value=1))
    E.play_card(g, "a", s["id"])
    assert E.current_player(g) == "a"


def test_draw2_next_draws_two_and_loses_turn():
    d = card("red", "draw2")
    g = three(card("red", value=1), a=[d, card("red", value=4)])
    before = len(g["hands"]["b"])
    E.play_card(g, "a", d["id"])
    assert len(g["hands"]["b"]) == before + 2
    assert E.current_player(g) == "c"


def test_wild4_accept_draws_four_and_skips():
    w4 = card("wild", "wild4")
    g = three(card("red", value=1), a=[w4, card("blue", value=4)])
    E.play_card(g, "a", w4["id"], "blue")
    assert g["pending"]["type"] == "wild4" and E.whose_action(g) == "b"
    before = len(g["hands"]["b"])
    E.respond_wild4(g, "b", challenge=False)
    assert len(g["hands"]["b"]) == before + 4
    assert E.current_player(g) == "c" and g["color"] == "blue"


def test_wild4_challenge_success_offender_draws_four():
    w4 = card("wild", "wild4")
    # "a" tinha vermelho (cor da mesa) => +4 ilegal
    g = three(card("red", value=1), a=[w4, card("red", value=4), card("blue", value=4)])
    E.play_card(g, "a", w4["id"], "blue")
    a_before, b_before = len(g["hands"]["a"]), len(g["hands"]["b"])
    assert E.respond_wild4(g, "b", challenge=True) is True
    assert len(g["hands"]["a"]) == a_before + 4
    assert len(g["hands"]["b"]) == b_before
    assert E.current_player(g) == "b"  # desafiante joga normalmente


def test_wild4_challenge_fail_challenger_draws_six():
    w4 = card("wild", "wild4")
    g = three(card("red", value=1), a=[w4, card("blue", value=4)])
    E.play_card(g, "a", w4["id"], "green")
    b_before = len(g["hands"]["b"])
    assert E.respond_wild4(g, "b", challenge=True) is False
    assert len(g["hands"]["b"]) == b_before + 6
    assert E.current_player(g) == "c"


def test_only_wild4_target_can_respond():
    w4 = card("wild", "wild4")
    g = three(card("red", value=1), a=[w4, card("blue", value=4)])
    E.play_card(g, "a", w4["id"], "green")
    with pytest.raises(E.GameError):
        E.respond_wild4(g, "c", False)
    with pytest.raises(E.GameError):
        E.draw_action(g, "b")


# --------------------------------------------------------------- comprar

def test_draw_then_play_drawn_card():
    drawn = card("red", value=8, cid="drawn")
    g = setup_game({"a": [card("blue", value=2), card("green", value=3)], "b": [card("red", value=2)]},
                   card("red", value=1), deck=[card("yellow", value=1), drawn])
    got = E.draw_action(g, "a")
    assert got["id"] == "drawn"
    assert g["pending"] == {"type": "drawn", "player": "a", "card_id": "drawn"}
    assert E.current_player(g) == "a"
    assert [c["id"] for c in E.playable_cards(g, "a")] == ["drawn"]
    E.play_card(g, "a", "drawn")
    assert E.current_player(g) == "b"


def test_draw_then_cannot_play_other_card_but_can_pass():
    other = card("red", value=5, cid="other")
    drawn = card("red", value=8, cid="drawn")
    g = setup_game({"a": [other, card("green", value=3)], "b": [card("red", value=2)]},
                   card("red", value=1), deck=[drawn])
    E.draw_action(g, "a")
    with pytest.raises(E.GameError):
        E.play_card(g, "a", "other")
    with pytest.raises(E.GameError):
        E.draw_action(g, "a")  # só uma compra por vez
    E.pass_turn(g, "a")
    assert E.current_player(g) == "b"


def test_draw_unplayable_passes_automatically():
    g = setup_game({"a": [card("blue", value=2)], "b": [card("red", value=2)]},
                   card("red", value=1), deck=[card("green", value=7, cid="g7")])
    E.draw_action(g, "a")
    assert g["pending"] is None and E.current_player(g) == "b"
    assert any(c["id"] == "g7" for c in g["hands"]["a"])


def test_cannot_pass_without_drawing():
    g = setup_game({"a": [card("red", value=2)], "b": [card("red", value=3)]}, card("red", value=1))
    with pytest.raises(E.GameError):
        E.pass_turn(g, "a")


def test_reshuffle_discard_when_deck_empty():
    top = card("red", value=1, cid="top")
    pile = [card("blue", value=v, cid=f"b{v}") for v in range(1, 6)]
    g = setup_game({"a": [card("green", value=2)], "b": [card("red", value=2)]}, top, deck=[])
    g["discard"] = pile + [top]
    E.draw_action(g, "a", rng=random.Random(3))
    assert g["discard"] == [top]
    assert len(g["deck"]) == 4 and len(g["hands"]["a"]) == 2
    assert any(ev["type"] == "shuffle" for ev in g["events"])


def test_draw_with_no_cards_anywhere_passes():
    g = setup_game({"a": [card("green", value=2)], "b": [card("red", value=2)]}, card("red", value=1), deck=[])
    assert E.draw_action(g, "a") is None
    assert E.current_player(g) == "b"


# --------------------------------------------------------------- UNO!

def test_uno_shout_before_playing_protects():
    a1 = card("red", value=2)
    g = setup_game({"a": [a1, card("blue", value=9)], "b": [card("red", value=3), card("red", value=4)]},
                   card("red", value=1))
    assert E.can_shout_uno(g, "a")
    E.shout_uno(g, "a")
    E.play_card(g, "a", a1["id"])
    assert g["vulnerable"] is None
    with pytest.raises(E.GameError):
        E.denounce(g, "b", "a")


def test_forgot_uno_denounce_gives_two_cards():
    a1 = card("red", value=2)
    g = setup_game({"a": [a1, card("blue", value=9)], "b": [card("red", value=3), card("red", value=4)],
                    "c": [card("green", value=3)]}, card("red", value=1))
    E.play_card(g, "a", a1["id"])
    assert g["vulnerable"] == "a"
    E.denounce(g, "c", "a")  # qualquer adversário pode denunciar
    assert len(g["hands"]["a"]) == 3
    assert g["vulnerable"] is None
    assert g["stats"]["c"]["denounces"] == 1 and g["stats"]["a"]["penalties"] == 1


def test_shout_right_after_playing_closes_window():
    a1 = card("red", value=2)
    g = setup_game({"a": [a1, card("blue", value=9)], "b": [card("red", value=3), card("red", value=4)]},
                   card("red", value=1))
    E.play_card(g, "a", a1["id"])
    E.shout_uno(g, "a")
    with pytest.raises(E.GameError):
        E.denounce(g, "b", "a")
    assert len(g["hands"]["a"]) == 1


def test_denounce_window_closes_when_next_player_acts():
    a1, b1 = card("red", value=2), card("red", value=3)
    g = setup_game({"a": [a1, card("blue", value=9)], "b": [b1, card("red", value=4)],
                    "c": [card("green", value=1)]}, card("red", value=1))
    E.play_card(g, "a", a1["id"])
    E.play_card(g, "b", b1["id"])
    with pytest.raises(E.GameError):
        E.denounce(g, "c", "a")


def test_cannot_denounce_self_or_shout_with_many_cards():
    g = setup_game({"a": [card("red", value=2)] * 3, "b": [card("red", value=3)]}, card("red", value=1))
    with pytest.raises(E.GameError):
        E.shout_uno(g, "a")
    with pytest.raises(E.GameError):
        E.denounce(g, "a", "a")


# --------------------------------------------------------------- fim de rodada / pontuação

def test_round_ends_when_hand_empties_and_scores_points():
    last = card("red", value=2)
    g = setup_game({"a": [last], "b": [card("blue", value=7), card("wild", "wild"), card("green", "skip")],
                    "c": [card("yellow", value=3)]}, card("red", value=1))
    g["uno_safe"] = ["a"]
    E.play_card(g, "a", last["id"])
    assert g["status"] == "game_over" and g["winner"] == "a"
    assert g["round_points"] == 7 + 50 + 20 + 3
    assert g["scores"]["a"] == 80
    with pytest.raises(E.GameError):
        E.draw_action(g, "b")


def test_last_card_draw2_still_makes_next_draw_and_counts():
    last = card("red", "draw2")
    g = setup_game({"a": [last], "b": [card("blue", value=1)]}, card("red", value=1),
                   deck=[card("green", value=4), card("green", value=5)])
    E.play_card(g, "a", last["id"])
    assert g["status"] == "game_over"
    assert len(g["hands"]["b"]) == 3 and g["round_points"] == 1 + 4 + 5


def test_target_score_plays_multiple_rounds():
    last = card("red", value=2)
    g = setup_game({"a": [last], "b": [card("blue", value=7)]}, card("red", value=1))
    g["target"] = 100
    E.play_card(g, "a", last["id"])
    assert g["status"] == "round_over" and g["scores"]["a"] == 7
    E.next_round(g, random.Random(1))
    assert g["status"] == "playing" and g["round"] == 2
    assert E.total_cards(g) == 108


def test_skip_player_host_action():
    g = setup_game({"a": [card("red", value=2)] * 2, "b": [card("red", value=3)]}, card("red", value=1))
    E.skip_player(g, "a")
    assert E.current_player(g) == "b"
    with pytest.raises(E.GameError):
        E.skip_player(g, "a")
