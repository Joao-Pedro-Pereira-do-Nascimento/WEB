"""Testes de fumaça da interface com streamlit.testing.v1.AppTest."""

import pytest
from streamlit.testing.v1 import AppTest

from conftest import ROOT
from game import engine as E
from game import rooms as R
from storage import LocalBackend

APP = str(ROOT / "app.py")


@pytest.fixture
def app_env(data_dir, monkeypatch):
    monkeypatch.setattr(R, "BOT_DELAY", 0.0)
    return LocalBackend(data_dir)


def new_app(guest=True):
    """App de teste. Por padrão já em "Jogar como convidado" (os testes antigos não usam conta)."""
    at = AppTest.from_file(APP, default_timeout=60)
    if guest:
        at.session_state["guest"] = True
    return at


def button(at, label):
    return next(b for b in at.button if b.label == label)


def keys(at):
    return [b.key for b in at.button]


def create(at, name="Ana", bots=0, room_name="Pantanal"):
    at.run()
    at.text_input(key="create_name").input(name)
    at.text_input(key="create_room_name").input(room_name)
    at.slider(key="create_bots").set_value(bots)
    button(at, "Criar sala").click().run()
    assert not at.exception, at.exception
    return at


def test_app_loads_home_and_tabs(app_env):
    at = new_app().run()
    assert not at.exception
    labels = [t.label for t in at.tabs]
    assert labels == ["Jogar", "Bestiário", "Ranking", "Regras"]
    html = "".join(m.value for m in at.markdown)
    assert "UNO FOLCLÓUNO" in html and "logo-svg" in html
    assert "Saci-Pererê" in html and "Mula sem Cabeça" in html  # bestiário
    assert {"Criar sala", "Entrar"} <= {b.label for b in at.button}


def test_create_room_requires_name(app_env):
    at = new_app().run()
    # o nome do jogador vem vazio (sem sugestão) e é obrigatório
    assert at.text_input(key="create_name").value == ""
    assert at.text_input(key="join_name").value == ""
    button(at, "Criar sala").click().run()
    assert any("nome" in e.value for e in at.error)
    assert "room" not in at.query_params


def test_create_room_add_bot_and_start(app_env):
    at = create(new_app(), "Ana")
    code = at.query_params["room"][0] if isinstance(at.query_params["room"], list) else at.query_params["room"]
    room = app_env.get_room(code)
    assert room and room["players"][0]["name"] == "Ana"
    assert "start" in keys(at) and at.button(key="start").disabled
    at.button(key="add_bot").click().run()
    assert len(app_env.get_room(code)["players"]) == 2
    at.button(key="start").click().run()
    assert not at.exception
    assert app_env.get_room(code)["status"] == "playing"
    assert any(k and k.startswith("play_") for k in keys(at))


def _play_until_over(at, max_steps=600):
    for _ in range(max_steps):
        assert not at.exception, at.exception
        ks = keys(at)
        if "to_lobby" in ks:
            return True
        for k in ("btn_uno", "btn_accept"):
            if k in ks:
                at.button(key=k).click().run()
                break
        else:
            picks = [k for k in ks if k and k.startswith("pick_")]
            playable = [b for b in at.button if b.key and b.key.startswith("play_") and not b.disabled]
            if picks:
                at.button(key=picks[0]).click().run()
            elif playable:
                playable[0].click().run()
            elif "btn_pass" in ks:
                at.button(key="btn_pass").click().run()
            elif "btn_draw" in ks:
                at.button(key="btn_draw").click().run()
            else:
                at.run()  # vez de bot: o fragmento faz o bot jogar
    return False


def test_full_game_against_bots_updates_ranking(app_env):
    at = create(new_app(), "Ana", bots=2)
    at.button(key="start").click().run()
    assert _play_until_over(at)
    code = at.query_params["room"]
    room = app_env.get_room(code)
    assert room["game"]["status"] == "game_over"
    assert E.total_cards(room["game"]) == 108
    at.run()
    rows = app_env.ranking()
    assert rows and rows[0]["name"] == "Ana" and rows[0]["games"] == 1
    assert "Ana" in "".join(m.value for m in at.markdown)  # aba Ranking
    at.button(key="to_lobby").click().run()
    assert app_env.get_room(code)["status"] == "lobby"
    assert "start" in keys(at)


def test_join_by_code_and_reconnect_by_token(app_env):
    room, host = R.new_room("QWERT", "Host")
    app_env.create_room("QWERT", room)
    at = new_app().run()
    at.text_input(key="join_code").input("qwert")
    at.text_input(key="join_name").input("Bia")
    button(at, "Entrar").click().run()
    assert not at.exception
    assert at.query_params["room"] == "QWERT"
    token = at.query_params["token"]
    stored = app_env.get_room("QWERT")
    bia = R.player_by_token(stored, token)
    assert bia["name"] == "Bia"
    # host começa a partida
    app_env.transact("QWERT", lambda r: R.start_game(r, host["id"]))
    hand = {c["id"] for c in app_env.get_room("QWERT")["game"]["hands"][bia["id"]]}
    # "recarregar a página": nova sessão só com a URL
    again = new_app()
    again.query_params["room"] = "QWERT"
    again.query_params["token"] = token
    again.run()
    assert not again.exception
    shown = {k[len("play_"):] for k in keys(again) if k and k.startswith("play_")}
    assert shown == hand


def test_join_errors(app_env):
    room, _ = R.new_room("ZXCVB", "Ana")
    app_env.create_room("ZXCVB", room)
    at = new_app().run()
    at.text_input(key="join_code").input("ZXCVB")
    at.text_input(key="join_name").input("ana")
    button(at, "Entrar").click().run()
    assert any("nome" in e.value for e in at.error)
    at.text_input(key="join_code").input("NOPEX")
    at.text_input(key="join_name").input("Caio")
    button(at, "Entrar").click().run()
    assert any("não encontrada" in e.value for e in at.error)


def test_invalid_reconnect_link_shows_warning(app_env):
    at = new_app()
    at.query_params["room"] = "AAAAA"
    at.query_params["token"] = "nada"
    at.run()
    assert not at.exception
    assert any("reconexão" in w.value for w in at.warning)


def test_wrong_turn_is_rejected_server_side(app_env):
    """Mesmo forçando a ação, o servidor recusa jogada fora da vez."""
    room, host = R.new_room("TURNX", "Ana")
    bot = R.add_bot(room, host["id"])
    app_env.create_room("TURNX", room)
    app_env.transact("TURNX", lambda r: R.start_game(r, host["id"]))
    g = app_env.get_room("TURNX")["game"]
    waiting = host["id"] if E.whose_action(g) == bot["id"] else bot["id"]
    with pytest.raises(E.GameError):
        app_env.transact("TURNX", lambda r: R.act(r, waiting, "draw"))
