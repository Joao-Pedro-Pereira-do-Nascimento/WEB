"""Duelo de biomas: matriz 4x4 completa, só visual (não muda o jogo), uma vez por jogada."""

import copy
import json
import random
import re
import xml.etree.ElementTree as ET

from game import engine as E
from game import rooms as R
from ui import duels as DU
from ui import effects as FX
from ui.styles import CSS

EMOJI = re.compile("[\\U0001F000-\\U0001FAFF\\u2600-\\u27BF\\u2B00-\\u2BFF\\u2300-\\u23FF\\uFE0F\\u200D]")


def _play(seq, color, kind="number"):
    return {"seq": seq, "type": "play", "player": "a", "color": color,
            "card": {"id": f"c{seq}", "kind": kind, "color": "wild" if kind in ("wild", "wild4") else color}}


def test_matrix_4x4_complete_and_distinct():
    pairs = [(a, b) for a in DU.COLORS for b in DU.COLORS]
    assert set(DU.DUELS) == set(pairs) and len(pairs) == 16
    kinds = {DU.DUELS[p][0] for p in pairs}
    texts = {DU.DUELS[p][1] for p in pairs}
    parts = {DU.DUELS[p][2] for p in pairs}
    assert len(kinds) == len(texts) == len(parts) == 16
    # o ciclo de vantagem
    assert DU.DUELS[("red", "blue")][1] == "Rios apagam o Fogo"
    assert DU.DUELS[("green", "red")][1] == "Fogo queima a Mata"
    assert DU.DUELS[("yellow", "green")][1] == "Mata vence o Cerrado"
    assert DU.DUELS[("blue", "yellow")][1] == "Cerrado seca os Rios"
    assert sorted(DU.BEATS) == sorted(DU.BEATS.values())


def test_every_duel_html_is_clean_and_non_blocking():
    for a in DU.COLORS:
        for b in DU.COLORS:
            for kind in ("number", "wild4"):
                evs = [_play(1, a), _play(2, b, kind)]
                d = DU.duel_for(evs, evs[1])
                assert d["from"] == a and d["to"] == b and d["sound"] in FX.SOUND_NAMES
                assert d["wild"] == (kind == "wild4")
                html = DU.duel_html(d)
                assert 'class="fx-layer duel' in html and not EMOJI.search(html)
                ET.fromstring(f"<root>{html}</root>")  # XML/HTML bem formado
    assert "pointer-events: none" in CSS and ".duel" in CSS
    assert "prefers-reduced-motion" in DU.DUEL_CSS and not EMOJI.search(DU.DUEL_CSS)


def test_previous_color_from_events():
    flip = {"seq": 1, "type": "flip", "card": {"kind": "number", "color": "green"}}
    assert DU.previous_color([flip, _play(2, "red")], 2) == "green"
    color = {"seq": 3, "type": "color", "color": "blue"}
    assert DU.previous_color([flip, color, _play(4, "red")], 4) == "blue"
    wild_flip = {"seq": 1, "type": "flip", "card": {"kind": "wild", "color": "wild"}}
    assert DU.duel_for([wild_flip, _play(2, "red")], _play(2, "red")) is None  # sem cor anterior: sem duelo
    assert DU.duel_for([], {"seq": 1, "type": "draw"}) is None


def test_duel_does_not_touch_game_state():
    room, host = R.new_room("ABCDE", "Ana")
    R.add_bot(room, host["id"])
    R.start_game(room, host["id"], rng=random.Random(3))
    game = room["game"]
    rng = random.Random(5)
    for _ in range(40):  # bots jogam dos dois lados
        pid = E.whose_action(game)
        from game import bots as B
        B.bot_step(game, pid, rng)
        if game["status"] != "playing":
            break
    before = json.dumps(game, sort_keys=True)
    snapshot = copy.deepcopy(game)
    plays = [ev for ev in game["events"] if ev["type"] == "play"]
    assert plays
    for ev in plays:
        d = DU.duel_for(game["events"], ev)
        if d:
            DU.duel_html(d)
    assert json.dumps(game, sort_keys=True) == before and game == snapshot


def test_duel_plays_once_and_special_effect_waits_in_queue():
    store = {}
    evs = [_play(1, "red"), _play(2, "blue", "number")]
    d = DU.duel_for(evs, evs[1])
    key = f"duel:ABCDE:g:{d['seq']}"
    assert FX.fx_push(store, key, DU.duel_html(d), 100.0, DU.DUEL_SECONDS, sounds=[d["sound"]])
    for t in (100.5, 101.0, 105.0):
        assert not FX.fx_push(store, key, DU.duel_html(d), t, DU.DUEL_SECONDS)  # nunca repete
    assert FX.fx_push(store, "ev:skip", "<b>skip</b>", 100.0, 3, after=True)
    assert "duel" in FX.fx_current(store, "fx", 101.0)
    assert FX.fx_current(store, "fx", 100.0 + DU.DUEL_SECONDS + .1) == "<b>skip</b>"
    assert FX.fx_current(store, "fx", 100.0 + DU.DUEL_SECONDS + 3.2) == ""
    assert store["sfx"]["names"] == ["b_blue"]


def test_new_effect_never_cuts_a_running_duel():
    """Regressão: o bot joga (duelo) e, no rerun seguinte, começa a minha vez ("turn",
    after=False). O duelo continua até o fim e o efeito da vez aparece logo depois."""
    store = {}
    t0 = 100.0
    assert FX.fx_push(store, "duel:R:g:1", "<b>duel1</b>", t0, DU.DUEL_SECONDS)
    assert FX.fx_push(store, "ev:R:g:turn:2", "<b>turn</b>", t0 + 0.5, 3.0)  # sem after
    assert FX.fx_current(store, "fx", t0 + 1.0) == "<b>duel1</b>"
    assert FX.fx_current(store, "fx", t0 + DU.DUEL_SECONDS + 0.05) == "<b>turn</b>"
    assert FX.fx_current(store, "fx", t0 + DU.DUEL_SECONDS + 2.9) == "<b>turn</b>"  # tempo cheio
    assert FX.fx_current(store, "fx", t0 + DU.DUEL_SECONDS + 3.1) == ""


def test_duel_queue_keeps_only_latest_duel():
    store = {}
    FX.fx_push(store, "duel:R:g:1", "<b>d1</b>", 0.0, DU.DUEL_SECONDS)
    FX.fx_push(store, "duel:R:g:2", "<b>d2</b>", 0.5, DU.DUEL_SECONDS)
    FX.fx_push(store, "duel:R:g:3", "<b>d3</b>", 1.0, DU.DUEL_SECONDS)
    assert FX.fx_current(store, "fx", 1.2) == "<b>d1</b>"
    assert FX.fx_current(store, "fx", DU.DUEL_SECONDS + 0.1) == "<b>d3</b>"  # d2 ficou velho
    # efeito comum (não duelo) pode ser substituído normalmente
    FX.fx_push(store, "ev:a", "<b>a</b>", 10.0, 3.0)
    FX.fx_push(store, "ev:b", "<b>b</b>", 10.5, 3.0)
    assert FX.fx_current(store, "fx", 10.6) == "<b>b</b>"
