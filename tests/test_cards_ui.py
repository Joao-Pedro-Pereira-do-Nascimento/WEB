"""Arte das cartas (SVG válido), bestiário, efeitos e sons."""

import xml.etree.ElementTree as ET

import pytest

from game import engine as E
from game.cards import CHARACTERS, KIND_CHARS, NUMBER_CHARS, back_svg, card_svg, card_tooltip, character_of, gallery
from ui import effects as FX
from ui import render as V


def test_every_card_has_valid_svg_and_character():
    seen = set()
    for c in E.build_deck():
        svg = card_svg(c)
        root = ET.fromstring(svg)
        assert root.tag.endswith("svg")
        assert "linearGradient" in svg  # arte com gradientes
        ch = character_of(c)
        assert ch in CHARACTERS
        assert CHARACTERS[ch]["name"] in card_tooltip(c)
        seen.add(ch)
    assert seen == set(CHARACTERS)
    ET.fromstring(back_svg())


def test_thematic_action_cards():
    assert KIND_CHARS == {"skip": "saci", "reverse": "curupira", "draw2": "cuca", "wild": "iara", "wild4": "mula"}
    assert len(NUMBER_CHARS) == 10 and len(set(NUMBER_CHARS)) == 10
    for kind in KIND_CHARS:
        assert CHARACTERS[KIND_CHARS[kind]].get("power")


def test_bestiary_lists_every_character_with_blurb():
    items = gallery()
    assert {it["char"] for it in items} == set(CHARACTERS)
    html = V.bestiary_html()
    for ch in CHARACTERS.values():
        assert V.esc(ch["name"]) in html
        assert len(ch["blurb"]) > 40


@pytest.mark.parametrize("etype", ["skip", "reverse", "draw2", "wild4", "wild", "uno", "denounce",
                                   "challenge_ok", "challenge_fail", "round_over", "game_over", "shuffle",
                                   "deal", "turn"])
def test_each_effect_has_overlay_with_event_id(etype):
    ev = {"type": etype, "seq": 77, "player": "a", "target": "b", "color": "red", "points": 10, "round": 1}
    html = FX.fx_html(ev, {"a": "Ana", "b": "Bia"}, "a")
    assert 'data-seq="77"' in html and "fx-layer" in html


def test_fx_priority_and_confetti():
    evs = [{"type": "play", "seq": 1}, {"type": "skip", "seq": 2}, {"type": "game_over", "seq": 3, "player": "a"}]
    assert FX.pick_fx(evs)["type"] == "game_over"
    assert "confetti" in FX.fx_html(evs[2], {"a": "Ana"}, "a")
    assert "VITÓRIA" in FX.fx_html(evs[2], {"a": "Ana"}, "a")
    assert FX.pick_fx([{"type": "play", "seq": 1}]) is None


def test_sounds_mapping_and_script():
    evs = [{"type": "play"}, {"type": "skip"}, {"type": "draw"}]
    assert FX.sounds_for(evs, my_turn_started=True) == ["play", "skip", "draw", "turn"]
    for needed in ["draw", "play", "skip", "reverse", "draw2", "wild4", "wild", "uno", "turn", "win", "fanfare"]:
        assert needed + ":" in FX.SOUND_ENGINE.replace(" ", "")
        assert needed in FX.SOUND_NAMES
    doc = FX.sound_script(["play", "inexistente", "uno"], 1234, muted=True)
    assert '["play", "uno"]' in doc and "1234" in doc and "muted = true" in doc
    assert "AudioContext" in doc and "window.parent" in doc
    assert "</script>" not in FX.SOUND_ENGINE


def test_render_helpers_produce_html():
    import random

    from game import rooms as R

    room, host = R.new_room("ABCDE", "Ana")
    R.add_bot(room, host["id"])
    R.start_game(room, host["id"], rng=random.Random(1))
    g = room["game"]
    assert "seat" in V.seats_html(room, host["id"], {host["id"]})
    assert "monte" in V.deck_html(g)
    assert "fly-in" in V.discard_html(g, True, True, g["seq"])
    assert "cor da mesa" in V.status_html(room, host["id"])
    assert "<table" in V.ranking_html([{"name": "Ana", "wins": 1, "games": 2}])
    assert "Ninguém" in V.ranking_html([])
