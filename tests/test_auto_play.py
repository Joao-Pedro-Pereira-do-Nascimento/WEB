"""Jogar automático (escolha do jogador) e reta final da música."""

import random

import pytest

from game import engine as E
from game import rooms as R
from test_app import app_env, create, keys, new_app  # noqa: F401 (fixture)
from ui import music as MU


def _room_with_bot(seed=3):
    room, host = R.new_room("ABCDE", "Ana")
    R.add_bot(room, host["id"])
    R.start_game(room, host["id"], rng=random.Random(seed), now=0.0)
    return room, host


def test_auto_play_requires_warning_confirmation():
    room, host = _room_with_bot()
    with pytest.raises(R.RoomError, match="imprecisas"):
        R.set_auto_play(room, host["id"], True)
    assert not room["players"][0].get("auto_play")
    assert R.set_auto_play(room, host["id"], True, confirmed=True)
    assert R.automated(room["players"][0])
    assert R.set_auto_play(room, host["id"], False)
    with pytest.raises(R.RoomError):
        R.set_auto_play(room, room["players"][1]["id"], True, confirmed=True)  # bot não


def test_auto_play_moves_are_valid_and_only_on_my_turn():
    room, host = _room_with_bot()
    R.set_auto_play(room, host["id"], True, confirmed=True)
    game = room["game"]
    rng = random.Random(1)
    now = 10.0
    for _ in range(400):
        if game["status"] != "playing":
            break
        actor = E.whose_action(game)
        before = (game["seq"], E.total_cards(game))
        assert R.bot_due(room, now) == actor  # bot e jogador automático: só quem tem a vez
        assert not R.run_bot(room, "outro", rng, now)
        other = next(p["id"] for p in room["players"] if p["id"] != actor)
        if other == host["id"]:
            assert not R.run_bot(room, host["id"], rng, now)  # fora da vez: não joga
        assert R.run_bot(room, actor, rng, now)
        assert game["seq"] > before[0] and E.total_cards(game) == 108  # passou pelo motor
        now += R.BOT_DELAY + 0.01
    assert game["status"] in ("round_over", "game_over")
    assert game.get("auto_moves", {}).get(host["id"], 0) > 0


def test_auto_play_shouts_uno_and_turns_off_at_game_over():
    room, host = _room_with_bot(seed=5)
    R.set_auto_play(room, host["id"], True, confirmed=True)
    game, rng, now, shouted = room["game"], random.Random(2), 10.0, False
    while game["status"] == "playing":
        actor = E.whose_action(game)
        R.run_bot(room, actor, rng, now)
        if len(game["hands"][host["id"]]) == 1 and game["status"] == "playing":
            assert game.get("vulnerable") != host["id"]  # automático sempre grita UNO
            shouted = True
        now += R.BOT_DELAY + 0.01
    assert game["status"] == "game_over"  # rodada única
    assert not room["players"][0].get("auto_play")  # desligou sozinho
    assert shouted  # chegou a 1 carta pelo menos uma vez, sempre protegido


def test_auto_play_ui_warns_then_enables(app_env):
    at = create(new_app(), "Ana", bots=1)
    at.button(key="start").click().run()
    code = at.query_params["room"]
    assert "auto_btn" in keys(at)
    at.button(key="auto_btn").click().run()
    assert "auto_yes" in keys(at) and "auto_no" in keys(at)
    assert any(R.AUTO_WARNING in m.value for m in at.markdown)
    assert not app_env.get_room(code)["players"][0].get("auto_play")  # só liga depois de confirmar
    at.button(key="auto_no").click().run()
    assert "auto_yes" not in keys(at) and not app_env.get_room(code)["players"][0].get("auto_play")
    at.button(key="auto_btn").click().run()
    at.button(key="auto_yes").click().run()
    assert not at.exception
    assert app_env.get_room(code)["players"][0]["auto_play"] is True
    assert "auto_off" in keys(at) and any("Automático" in m.value for m in at.markdown)
    at.button(key="auto_off").click().run()
    assert not app_env.get_room(code)["players"][0].get("auto_play")


def test_tension_level_from_hands():
    game = {"status": "playing", "hands": {"a": [1] * 7, "b": [1] * 5}}
    assert MU.tension_level(game) == 0
    game["hands"]["b"] = [1] * 3
    assert MU.tension_level(game) == 1
    game["hands"]["a"] = [1]
    assert MU.tension_level(game) == 2
    game["hands"]["a"] = [1] * 9  # comprou: volta ao normal
    game["hands"]["b"] = [1] * 8
    assert MU.tension_level(game) == 0
    players = [{"id": "a"}, {"id": "b", "left": True}]
    game["hands"]["b"] = [1]
    assert MU.tension_level(game, players) == 0  # quem saiu não conta
    assert MU.tension_level({"status": "round_over", "hands": {"a": [1]}}) == 0
    assert MU.tension_level(None) == 0


def test_tension_reaches_js_without_restarting():
    doc = MU.tension_script(2)
    assert "W.__unoMusic.setTension(2)" in doc and "W.__unoMusicTension = 2" in doc
    assert "set(" not in doc.replace("setTension", "")  # não troca trilha nem reinicia
    js = MU.engine_js()
    assert "M.setTension = function(level)" in js
    assert "if (T.i % 16 === 0) T.lvl" in js  # muda só no começo do compasso
    assert "TEMPO = [1, 1.18, 1.25]" in js


def test_tension_passed_by_app(app_env):
    at = create(new_app(), "Ana", bots=1)
    assert at.session_state["music_tension"] == 0  # lobby
    at.button(key="start").click().run()
    code = at.query_params["room"]
    room = app_env.get_room(code)
    assert at.session_state["music_tension"] == MU.tension_level(room["game"], room["players"])
