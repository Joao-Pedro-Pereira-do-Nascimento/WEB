"""Nome da sala, código colado de qualquer jeito e convite por link (?sala=)."""

import pytest
from streamlit.testing.v1 import AppTest

from conftest import ROOT
from game import rooms as R
from storage import LocalBackend
from ui import render as V
from ui import effects as FX


@pytest.mark.parametrize("raw", ["KXPTZ", "kxptz", "  kx ptz ", "K-X-P-T-Z", "http://192.168.0.10:8501/?sala=kxptz",
                                 "https://uno.streamlit.app/?sala=KXPTZ&x=1", "https://uno.streamlit.app/?room=KXPTZ&token=abc"])
def test_extract_code_accepts_pasted_text(raw):
    assert R.extract_code(raw) == "KXPTZ"


def test_extract_code_garbage():
    assert R.extract_code("") == "" and R.extract_code(None) == ""
    assert len(R.extract_code("abcdefghij")) == R.CODE_LENGTH


def test_room_name_default_sanitized_and_limited():
    room, _ = R.new_room("ABCDE", "Ana")
    assert room["name"] in R.HABITATS                     # vazio: habitat sorteado
    room, _ = R.new_room("ABCDE", "Ana", name="   ")
    assert room["name"] in R.HABITATS
    room, _ = R.new_room("ABCDE", "Ana", name="  Roda   do  Saci  ")
    assert room["name"] == "Roda do Saci"
    long = R.clean_room_name("x" * 60)
    assert len(long) == R.MAX_ROOM_NAME
    assert R.clean_room_name("<script>Rio\x00 Negro</script>") == "scriptRio Negro/script"
    assert R.clean_room_name("Fogueira \U0001F525\uFE0F") == "Fogueira"


def test_old_room_without_name_shows_code():
    room, _ = R.new_room("OLDRM", "Ana")
    room.pop("name")
    assert R.room_title(room) == "OLDRM"
    head = V.room_header(room, "http://x/?sala=OLDRM")
    assert "OLDRM" in head and 'data-copy="OLDRM"' in head and 'data-copy="http://x/?sala=OLDRM"' in head
    assert "OLDRM" in FX.portal_html("OLDRM", "k", R.room_title(room))


def test_room_header_and_portal_show_name():
    room, _ = R.new_room("ABCDE", "Ana", name="Igarapé")
    head = V.room_header(room, "http://x/?sala=ABCDE")
    assert 'class="room-name">Igarapé<' in head and "Copiar código" in head and "Copiar convite" in head
    portal = FX.portal_html("ABCDE", "k", "Igarapé")
    assert "código ABCDE" in portal and "entrando na sala" in portal
    assert "data-paste" in V.paste_button(".st-key-join_code input") and "paste-hint" in V.paste_button("x")
    doc = FX.sound_script([], 1)
    assert "execCommand('copy')" in doc and "readText" in doc and "isSecureContext" in doc


def _app():
    at = AppTest.from_file(str(ROOT / "app.py"), default_timeout=60)
    at.session_state["guest"] = True  # formulários de convidado (sem conta)
    return at


def test_invite_link_prefills_join_code(data_dir):
    at = _app()
    at.query_params["sala"] = "kxptz"
    at.run()
    assert not at.exception
    assert at.text_input(key="join_code").value == "KXPTZ"


def test_join_with_pasted_link_and_named_room(data_dir):
    be = LocalBackend(data_dir)
    room, _ = R.new_room("QWERT", "Host", name="Rio Negro")
    be.create_room("QWERT", room)
    at = _app().run()
    at.text_input(key="join_code").input("http://192.168.0.10:8501/?sala=qwert")
    at.text_input(key="join_name").input("Bia")
    next(b for b in at.button if b.label == "Entrar").click().run()
    assert not at.exception
    assert at.query_params["room"] == "QWERT"
    html = "".join(m.value for m in at.markdown)
    assert "Rio Negro" in html
    assert any("Você entrou em Rio Negro" in t.value for t in at.toast)


def test_create_with_room_name(data_dir):
    be = LocalBackend(data_dir)
    at = _app().run()
    at.text_input(key="create_name").input("Ana")
    at.text_input(key="create_room_name").input("  Roda da Cuca ")
    next(b for b in at.button if b.label == "Criar sala").click().run()
    code = at.query_params["room"]
    assert be.get_room(code)["name"] == "Roda da Cuca"


def test_empty_room_name_is_blocked_not_chosen_silently(data_dir):
    at = _app().run()
    assert at.text_input(key="create_room_name").value == ""      # nunca preenchido sozinho
    at.text_input(key="create_name").input("Bia")
    next(b for b in at.button if b.label == "Criar sala").click().run()
    assert "room" not in at.query_params
    assert any("Sortear" in e.value for e in at.error)


def test_draw_button_fills_habitat_and_never_repeats(data_dir):
    at = _app().run()
    seen = []
    for _ in range(6):
        at.button(key="draw_room").click().run()
        value = at.text_input(key="create_room_name").value
        assert value in R.HABITATS
        if seen:
            assert value != seen[-1]
        seen.append(value)
    # editável depois do sorteio
    at.text_input(key="create_room_name").input(seen[-1] + " Sul").run()
    assert at.text_input(key="create_room_name").value == seen[-1] + " Sul"


def test_suggestion_chips_fill_room_name(data_dir):
    at = _app().run()
    chips = at.session_state["room_chip_options"]
    assert len(chips) == 4 and set(chips) <= set(R.HABITATS)
    at.button_group(key="room_chips").set_value(chips[2]).run()
    assert at.text_input(key="create_room_name").value == chips[2]


def test_suggest_name_excludes_current():
    import random

    rng = random.Random(1)
    for h in R.HABITATS:
        for _ in range(20):
            assert R.suggest_name(rng, exclude=h) != h
