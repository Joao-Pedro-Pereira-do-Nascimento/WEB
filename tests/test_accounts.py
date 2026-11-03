"""Contas: senha com hash, cadastro único, login, redefinição, limite de tentativas,
sessões, conta Google, volta à sala pela conta e ranking por conta."""

import datetime as dt
import json
import threading

import pytest
from streamlit.testing.v1 import AppTest

from conftest import ROOT
from game import accounts as AC
from game import rooms as R
from storage import LocalBackend
from storage import rtdb as RT
from test_rtdb_fake import FakeRTDB

BIRTH = "2001-04-09"


@pytest.fixture
def be(tmp_path):
    return LocalBackend(tmp_path / "data")


@pytest.fixture
def rt(monkeypatch):
    monkeypatch.setattr(RT, "CACHE_TTL", 0.0)
    fake = FakeRTDB()
    be = RT.RTDBBackend(None, "https://exemplo-default-rtdb.firebaseio.com", db_module=fake, app="fake-app")
    be.fake = fake
    return be


def test_password_hash_and_verify():
    rec = AC.hash_password("segredo1")
    assert rec["algo"] == "pbkdf2_sha256" and rec["iter"] >= 200_000 and len(rec["salt"]) == 32
    assert "segredo1" not in json.dumps(rec)
    assert AC.verify_password("segredo1", rec)
    assert not AC.verify_password("segredo2", rec) and not AC.verify_password("", rec)
    assert AC.hash_password("segredo1")["hash"] != rec["hash"]  # salt diferente a cada conta


def test_register_validations_and_stored_without_plain_password(be):
    with pytest.raises(AC.AccountError, match="6"):
        AC.register(be, "Ana", BIRTH, "123", "123")
    with pytest.raises(AC.AccountError, match="iguais"):
        AC.register(be, "Ana", BIRTH, "segredo1", "segredo2")
    with pytest.raises(AC.AccountError):
        AC.register(be, "Ana", "2999-01-01", "segredo1", "segredo1")
    with pytest.raises(AC.AccountError):
        AC.register(be, "a", BIRTH, "segredo1", "segredo1")
    acc = AC.register(be, "Ana Lú", BIRTH, "segredo1", "segredo1")
    assert acc == {"key": "ana-lu", "name": "Ana Lú", "kind": "password", "avatar": None, "email": ""}
    raw = json.dumps(be.doc_get("users", "ana-lu"))
    assert "segredo1" not in raw and "pbkdf2_sha256" in raw
    # mesmo nome sem diferenciar maiúsculas/acentos
    with pytest.raises(AC.AccountError, match="já existe"):
        AC.register(be, "ANA LU", BIRTH, "outra123", "outra123")


def test_register_concurrent_same_name_only_one_wins(be):
    results = []

    def go(i):
        try:
            AC.register(be, "Bia", BIRTH, f"senha{i}xx", f"senha{i}xx")
            results.append("ok")
        except AC.AccountError:
            results.append("dup")

    threads = [threading.Thread(target=go, args=(i,)) for i in range(8)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert results.count("ok") == 1 and results.count("dup") == 7


def test_register_race_in_rtdb_transaction(rt):
    # outro cliente cadastra "Ana" no meio da transação: a repetição vê o cadastro e recusa
    rt.fake.on_transaction_read = lambda: AC.register(rt, "Ana", BIRTH, "primeira1", "primeira1")
    with pytest.raises(AC.AccountError, match="já existe"):
        AC.register(rt, "ANA", BIRTH, "segunda22", "segunda22")
    assert AC.login(rt, "ana", "primeira1")["name"] == "Ana"
    node = rt.fake.tree["uno"]["users"]["ana"]
    assert isinstance(node["data"], str) and "primeira1" not in node["data"]


def test_login_right_and_wrong(be):
    AC.register(be, "Caio", BIRTH, "segredo1", "segredo1")
    assert AC.login(be, "caio", "segredo1")["key"] == "caio"
    assert AC.login(be, "  CAIO ", "segredo1")["name"] == "Caio"
    for user, pw in (("caio", "errada"), ("ninguem", "segredo1"), ("", "x")):
        with pytest.raises(AC.AccountError, match="incorretos"):
            AC.login(be, user, pw)


def test_login_rate_limit(be):
    AC.register(be, "Dani", BIRTH, "segredo1", "segredo1")
    for _ in range(AC.MAX_FAILS):
        with pytest.raises(AC.AccountError, match="incorretos"):
            AC.login(be, "dani", "errada", now=1000.0)
    with pytest.raises(AC.AccountError, match="Muitas tentativas"):
        AC.login(be, "dani", "segredo1", now=1001.0)  # até a senha certa espera
    assert AC.login(be, "dani", "segredo1", now=1000.0 + AC.FAIL_WINDOW + 1)["key"] == "dani"


def test_reset_password_right_wrong_and_limit(be):
    AC.register(be, "Edu", BIRTH, "segredo1", "segredo1")
    with pytest.raises(AC.AccountError, match="não conferem"):
        AC.reset_password(be, "edu", "2001-04-10", "novasenha", "novasenha", now=100.0)
    with pytest.raises(AC.AccountError, match="não conferem"):  # mesma mensagem para usuário que não existe
        AC.reset_password(be, "zeca", BIRTH, "novasenha", "novasenha", now=100.0)
    acc = AC.reset_password(be, "EDU", dt.date(2001, 4, 9), "novasenha", "novasenha", now=200.0)
    assert acc["key"] == "edu"
    assert AC.login(be, "edu", "novasenha")
    with pytest.raises(AC.AccountError):
        AC.login(be, "edu", "segredo1")
    for _ in range(AC.MAX_FAILS):
        with pytest.raises(AC.AccountError, match="não conferem"):
            AC.reset_password(be, "edu", "1990-01-01", "outra123", "outra123", now=300.0)
    with pytest.raises(AC.AccountError, match="Muitas tentativas"):
        AC.reset_password(be, "edu", BIRTH, "outra123", "outra123", now=301.0)


def test_sessions_create_validate_expire_logout(be):
    AC.register(be, "Fabi", BIRTH, "segredo1", "segredo1", now=0.0)
    tok = AC.create_session(be, "fabi", now=1000.0)
    assert len(tok) >= 40
    assert be.doc_get("sessions", tok) is None  # só o hash fica salvo
    assert AC.session_account(be, tok, now=2000.0)["key"] == "fabi"
    assert AC.session_account(be, "token-falso", now=2000.0) is None
    assert AC.session_account(be, tok, now=1000.0 + AC.SESSION_SECONDS + 1) is None  # expirou
    assert AC.session_account(be, tok, now=2000.0) is None  # e foi apagada
    tok2 = AC.create_session(be, "fabi", now=3000.0)
    AC.logout(be, tok2)
    assert AC.session_account(be, tok2, now=3001.0) is None
    tok3 = AC.create_session(be, "fabi", now=4000.0)
    AC.reset_password(be, "fabi", BIRTH, "nova1234", "nova1234", now=5000.0)
    assert AC.session_account(be, tok3, now=5001.0) is None  # trocar a senha derruba sessões antigas


def test_google_account_and_profile(be):
    acc = AC.google_account(be, "1234567890", "Gabi Souza", "gabi@exemplo.com")
    assert acc["key"] == "g_1234567890" and acc["kind"] == "google" and acc["name"] == "Gabi Souza"
    assert AC.google_account(be, "1234567890", "Outro Nome")["name"] == "Gabi Souza"  # não sobrescreve
    assert AC.update_profile(be, acc["key"], name="Gabi", avatar="iara")["name"] == "Gabi"
    assert AC.get_account(be, acc["key"])["avatar"] == "iara"
    with pytest.raises(AC.AccountError):
        AC.login(be, "g_1234567890", "")  # conta Google não entra por senha
    AC.register(be, "Hugo", BIRTH, "segredo1", "segredo1")
    with pytest.raises(AC.AccountError):
        AC.update_profile(be, "hugo", name="Outro")


def test_rejoin_active_room_by_account(be):
    AC.register(be, "Iris", BIRTH, "segredo1", "segredo1")
    room, host = R.new_room("ABCDE", "Iris", account="iris")
    be.create_room("ABCDE", room)
    AC.remember_room(be, "iris", "ABCDE", host["token"])
    got = AC.active_room(be, "iris")
    assert got and got[1]["id"] == host["id"] and got[1]["token"] == host["token"]
    # entrar de novo pelo código com a mesma conta devolve o mesmo lugar, mesmo com a partida rolando
    be.transact("ABCDE", lambda r: R.add_bot(r, host["id"]))
    be.transact("ABCDE", lambda r: R.start_game(r, host["id"]))
    _, again = be.transact("ABCDE", lambda r: R.join_room(r, "Iris", None, "iris"))
    assert again["id"] == host["id"] and again["token"] == host["token"]
    assert len(be.get_room("ABCDE")["players"]) == 2
    AC.forget_room(be, "iris")
    assert AC.active_room(be, "iris") is None


def test_active_room_ignores_finished_or_left(be):
    room, host = R.new_room("ABCDE", "Joel", account="joel")
    R.add_bot(room, host["id"])
    R.start_game(room, host["id"])
    room["game"]["status"] = "game_over"
    be.create_room("ABCDE", room)
    AC.register(be, "Joel", BIRTH, "segredo1", "segredo1")
    AC.remember_room(be, "joel", "ABCDE", host["token"])
    assert AC.active_room(be, "joel") is None
    AC.remember_room(be, "joel", "ZZZZZ", host["token"])
    assert AC.active_room(be, "joel") is None


def test_ranking_uses_account_key():
    room, host = R.new_room("ABCDE", "Kika", account="g_99")
    guest = R.join_room(room, "Lia")
    R.start_game(room, host["id"])
    game = room["game"]
    game["stats"] = {host["id"]: {"cards_played": 1}, guest["id"]: {"cards_played": 2}}
    keys = {k for k, _, _ in R.stats_entries(room)}
    assert keys == {"g_99", "lia"}  # convidado continua pela chave do nome (compatível)


def _empty_secrets(monkeypatch):
    """Ignora o .streamlit/secrets.toml real: o app roda como se não houvesse secrets."""
    import streamlit as st
    from streamlit.runtime.secrets import Secrets

    empty = Secrets()
    empty._secrets = {}
    monkeypatch.setattr(st, "secrets", empty)


def test_user_key_never_falls_back_to_generic_name(be):
    assert AC.user_key("  Ana   Lú ") == "ana-lu" and AC.user_key("") == "" and AC.user_key("***") == ""
    AC.register(be, "Jogador", BIRTH, "segredo1", "segredo1")
    with pytest.raises(AC.AccountError, match="incorretos"):
        AC.login(be, "", "segredo1")  # vazio não cai na conta "jogador"
    with pytest.raises(AC.AccountError):
        AC.register(be, "***", BIRTH, "segredo1", "segredo1")


def test_app_with_auth_shows_google_button_calling_st_login(data_dir, monkeypatch):
    import streamlit as st

    calls = []
    monkeypatch.setattr(st, "login", lambda *a, **k: calls.append(a))
    at = AppTest.from_file(str(ROOT / "app.py"), default_timeout=60)
    at.secrets["auth"] = {"redirect_uri": "http://localhost:8501/oauth2callback", "cookie_secret": "x" * 32,
                          "google": {"client_id": "id", "client_secret": "s",
                                     "server_metadata_url": "https://accounts.google.com/.well-known/openid-configuration"}}
    at.run()
    assert not at.exception
    btn = at.button(key="google_login")
    assert btn.label == "Entrar com Google" and not btn.disabled
    btn.click().run()
    assert calls == [("google",)]


def test_app_without_auth_shows_login_and_guest(data_dir, monkeypatch):
    _empty_secrets(monkeypatch)
    at = AppTest.from_file(str(ROOT / "app.py"), default_timeout=60).run()
    assert not at.exception
    labels = {b.label: b for b in at.button}
    assert labels["Entrar com Google"].disabled  # sem [auth] nos secrets
    assert "Jogar como convidado" in labels and "Entrar" in labels
    # cria a conta e já entra; os formulários não pedem nome
    at.segmented_control(key="auth_mode").set_value("Criar conta").run()
    at.text_input(key="signup_user").input("Mara")
    at.date_input(key="signup_birth").set_value(dt.date(2000, 1, 2))
    at.text_input(key="signup_pw").input("segredo1")
    at.text_input(key="signup_pw2").input("segredo1")
    at.button(key="signup_submit").click().run()
    assert not at.exception and not at.error, [e.value for e in at.error]
    assert at.session_state["account"]["key"] == "mara"
    assert "create_name" not in [t.key for t in at.text_input]
    at.text_input(key="create_room_name").input("Pantanal")
    at.button(key="create_submit").click().run()
    assert not at.exception
    be = LocalBackend(data_dir)
    code = at.query_params["room"]
    room = be.get_room(code)
    assert room["players"][0]["account"] == "mara" and room["players"][0]["name"] == "Mara"
    assert be.doc_get("users", "mara")["room"]["code"] == code
    # outro navegador: entra com usuário e senha e aparece "Voltar para a sala"
    at2 = AppTest.from_file(str(ROOT / "app.py"), default_timeout=60).run()
    at2.text_input(key="login_user").input("MARA")
    at2.text_input(key="login_pw").input("segredo1")
    at2.button(key="login_submit").click().run()
    assert not at2.exception and at2.session_state["account"]["key"] == "mara"
    back = at2.button(key="back_room")
    assert back.label.startswith("Voltar para a sala Pantanal")
    back.click().run()
    assert at2.query_params["room"] == code and at2.query_params["token"] == room["players"][0]["token"]
    # sair: invalida a sessão e volta para o formulário de login
    tok = at2.session_state["sess_token"]
    at2.button(key="logout_btn").click().run()
    assert not at2.exception and "account" not in at2.session_state
    assert AC.session_account(be, tok) is None


def test_every_backend_implements_the_whole_contract():
    """Todos os armazenamentos implementam cada método de ``Backend`` (incl. doc_get/doc_update
    usados pelas contas): nenhum herda o ``NotImplementedError`` da base."""
    from storage.base import Backend
    from storage.firebase import FirebaseBackend

    contract = [n for n, v in vars(Backend).items() if callable(v) and not n.startswith("_")]
    assert {"doc_get", "doc_update", "get_room", "transact", "record_stats"} <= set(contract)
    for cls in (LocalBackend, FirebaseBackend, RT.RTDBBackend):
        for name in contract:
            assert getattr(cls, name) is not getattr(Backend, name), f"{cls.__name__}.{name} faltando"
    # e as contas só usam métodos do contrato
    import inspect
    import re
    used = set(re.findall(r"\bbe\.(\w+)\(", inspect.getsource(AC)))
    assert used and used <= set(contract), used - set(contract)


def test_rtdb_docs_use_transaction_and_safe_keys(rt):
    calls = []
    orig = rt.fake.on_transaction_read
    rt.fake.on_transaction_read = lambda: calls.append(1)
    assert rt.doc_update("users", "a.b/c#d", lambda cur: ({"x": 1}, "ok")) == "ok"
    rt.fake.on_transaction_read = orig
    assert calls  # passou por transaction()
    assert rt.doc_get("users", "a.b/c#d") == {"x": 1}
    keys = list(rt.fake.tree["uno"]["users"])
    assert keys == ["a%2Eb%2Fc%23d"]
    assert rt.doc_update("users", "a.b/c#d", lambda cur: (None, cur)) == {"x": 1}
    assert rt.doc_get("users", "a.b/c#d") is None


def test_full_account_flow_in_rtdb_fake(rt):
    acc = AC.register(rt, "Nina Ó", BIRTH, "segredo1", "segredo1")
    assert acc["key"] == "nina-o" and AC.login(rt, "nina o", "segredo1")["key"] == "nina-o"
    tok = AC.create_session(rt, "nina-o")
    assert set(AC._token_hash(tok)) <= set("0123456789abcdef")
    assert AC.session_account(rt, tok)["key"] == "nina-o"
    with pytest.raises(AC.AccountError):
        AC.login(rt, "nina-o", "errada")
    assert "login-nina-o" in rt.fake.tree["uno"]["limits"]
    AC.reset_password(rt, "Nina O", BIRTH, "nova1234", "nova1234", now=__import__("time").time() + 1)
    assert AC.session_account(rt, tok) is None and AC.login(rt, "nina-o", "nova1234")
    AC.logout(rt, tok)
    g = AC.google_account(rt, "123", "Gil")
    assert rt.doc_get("users", g["key"])["kind"] == "google"
