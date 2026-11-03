"""Músicas de fundo: trilha certa em cada tela, volume do jogo menor, respeita o mudo,
não duplica em reruns, ducking com os efeitos e botão "Música"."""

import re

from streamlit.testing.v1 import AppTest

from conftest import ROOT
from ui import music as MU


def test_script_flags_and_guard():
    on = MU.music_script("home", False)
    assert 'W.__unoMusic.set("home", false)' in on
    assert 'W.__unoMusic.set("home", true)' in MU.music_script("home", True)  # mudo
    assert 'W.__unoMusic.set("game", false)' in MU.music_script("game", False)  # sala/partida
    assert 'W.__unoMusic.set("", false)' in MU.music_script("qualquer", False)
    js = MU.engine_js()
    assert "if (W.__unoMusic) return;" in js  # guarda: o motor é instalado uma vez só
    assert "if (!W.__unoMusic)" in on  # o carregador também confere antes de injetar
    assert "if (T.playing) return;" in js  # set() repetido não reinicia o sequenciador
    assert "window.parent" in on


def test_engine_features():
    js = MU.engine_js()
    assert "Música" in js and "uno-music" in js and "<svg" in js  # botão próprio com ícone SVG
    assert "localStorage" in js and MU.STORAGE_KEY in js  # preferência persistente
    assert "pointerdown" in js and "touchend" in js and ".resume()" in js  # começa no 1o gesto (iOS)
    assert "ramp(T.master.gain, T.vol, T.fadeIn)" in js and "ramp(T.master.gain, 0.0001, 1.6)" in js  # fades
    assert "VOL_HOME = 0.25" in js
    assert "currentTime + LOOK" in js  # agendamento com lookahead
    home_bpm, game_bpm = (int(x) for x in re.findall(r"const BPM = (\d+)", js))
    assert 110 <= home_bpm <= 130 and 80 <= game_bpm <= 96
    assert "__" not in js.replace("__unoMusic", "")  # nenhum marcador sem substituir


def test_game_track_quieter_and_ducks_with_effects():
    assert 0.3 <= MU.GAME_VOLUME / MU.VOLUME <= 0.42
    js = MU.engine_js()
    assert f"VOL_GAME = {MU.GAME_VOLUME}" in js
    assert "M.duck = function(names, seq)" in js and "'win'" in js and "'defeat'" in js
    assert "if (seq <= M.duckSeq) return;" in js  # o mesmo efeito não abaixa duas vezes
    from ui import effects as FX
    doc = FX.sound_script(["play"], 7)
    assert "W.__unoMusic.duck([\"play\"], 7)" in doc


def test_music_only_on_home_screen(data_dir):
    at = AppTest.from_file(str(ROOT / "app.py"), default_timeout=60).run()
    assert not at.exception
    assert at.session_state["music_state"] == ("home", False)
    at.toggle(key="muted").set_value(True).run()
    assert at.session_state["music_state"] == ("home", True)
    at.toggle(key="muted").set_value(False).run()
    at.button(key="guest_btn").click().run()
    at.text_input(key="create_name").input("Rui")
    at.text_input(key="create_room_name").input("Caatinga")
    at.button(key="create_submit").click().run()
    assert not at.exception and at.query_params.get("room")
    assert at.session_state["music_state"] == ("game", False)  # dentro da sala: crossfade para a trilha do jogo
