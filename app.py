"""UNO FOLCLÓUNO — jogo de cartas online com personagens do folclore brasileiro.

Rode com:  streamlit run app.py

Arquitetura (resumo):
- ``game/engine.py``  regras puras do UNO (validação do lado do servidor);
- ``game/rooms.py``   salas, anfitrião, bots, reconexão;
- ``storage/``        armazenamento compartilhado (arquivos locais, Firebase Realtime Database ou Firestore);
- ``ui/``             logo e ícones em SVG, CSS do tema, animações, sons (Web Audio API).

Cada navegador guarda ``?room=CODIGO&token=SEGREDO`` na URL: recarregar a página
(ou abrir o link de reconexão em outro aparelho) devolve o mesmo lugar à mesa.
A mesa é atualizada por um ``st.fragment`` que relê o estado a cada ~1 s.
"""

from __future__ import annotations

import os
import time
from pathlib import Path

import streamlit as st
from streamlit.errors import StreamlitAPIException

from game import accounts as AC
from game import avatars as AV
from game import engine as E
from game import rooms as R
from game.cards import BIOMES, CHARACTERS, KIND_CHARS, NUMBER_CHARS
from storage import NoChange, RoomNotFound, backend_label, make_backend
from ui import duels as DU
from ui import effects as FX
from ui import music as MU
from ui import render as V
from ui.icons import icon
from ui.styles import CSS, ambient_html

ROOT = Path(__file__).resolve().parent
os.environ.setdefault("UNO_DATA_DIR", str(ROOT / ".data"))

COLOR_ORDER = {"red": 0, "yellow": 1, "green": 2, "blue": 3, "wild": 4}
KIND_ORDER = {"number": 0, "skip": 1, "reverse": 2, "draw2": 3, "wild": 4, "wild4": 5}
TARGET_LABELS = {0: "Rodada única", 100: "100 pontos", 200: "200 pontos", 500: "500 pontos"}
FAVICON = ROOT / "assets" / "favicon.png"

st.set_page_config(page_title="Uno Folclóuno", page_icon=str(FAVICON) if FAVICON.exists() else None,
                   layout="wide", initial_sidebar_state="collapsed")


# =========================================================================== infraestrutura

@st.cache_resource(show_spinner=False)
def _backend_for(data_dir: str, mode: str):
    try:
        secrets = st.secrets
    except Exception:  # sem secrets.toml
        secrets = None
    return make_backend(secrets)


def backend():
    be, _warning = _backend_for(os.environ.get("UNO_DATA_DIR", ".data"), os.environ.get("UNO_BACKEND", ""))
    return be


def backend_warning() -> str | None:
    return _backend_for(os.environ.get("UNO_DATA_DIR", ".data"), os.environ.get("UNO_BACKEND", ""))[1]


def ss_default(key: str, value):
    if key not in st.session_state:
        st.session_state[key] = value
    return st.session_state[key]


def flash(msg: str) -> None:
    st.session_state.setdefault("_flash", []).append(msg)


def show_flash() -> None:
    for msg in st.session_state.pop("_flash", []):
        st.toast(msg)


def transact(code: str, fn):
    """Executa ``fn(sala)`` de forma atômica. Erros de regra viram aviso."""
    try:
        return backend().transact(code, fn)
    except NoChange:
        return None
    except RoomNotFound:
        flash("Essa sala não existe (ou expirou).")
    except E.GameError as exc:
        flash(str(exc))
    return None


def lan_ip() -> str | None:
    """IP desta máquina na rede local (sem enviar pacotes: UDP só escolhe a rota)."""
    import socket
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.connect(("10.255.255.255", 1))
            ip = s.getsockname()[0]
    except OSError:
        return None
    return None if ip.startswith("127.") else ip


def base_url() -> str:
    """Endereço público do app para convites, sempre terminando em ``/``.

    Ordem: ``public_url`` nos secrets ou ``UNO_PUBLIC_URL`` > URL da página
    (no Streamlit Cloud já é a pública) > ``localhost`` trocado pelo IP da rede,
    para o link funcionar em outro aparelho no mesmo Wi-Fi.
    """
    from urllib.parse import urlsplit, urlunsplit

    try:
        url = str(st.secrets.get("public_url", "") or "")
    except Exception:
        url = ""
    url = url or os.environ.get("UNO_PUBLIC_URL", "")
    if not url:
        try:
            url = st.context.url or ""
        except Exception:
            url = ""
        url = url or "http://localhost:8501/"
        parts = urlsplit(url)
        if parts.hostname in ("localhost", "127.0.0.1", "0.0.0.0", "::1"):
            ip = lan_ip()
            if ip:
                netloc = ip + (f":{parts.port}" if parts.port else "")
                url = urlunsplit((parts.scheme, netloc, parts.path, "", ""))
    url = url.split("?")[0].split("#")[0]
    return url if url.endswith("/") else url + "/"


def refresh() -> None:
    """Redesenha só a mesa (fragmento); fora de um fragmento, o app inteiro."""
    try:
        st.rerun(scope="fragment")
    except StreamlitAPIException:
        st.rerun()


def go_home() -> None:
    st.query_params.clear()
    st.session_state.pop("pending_wild", None)
    FX.fx_forget(st.session_state, "portal:")  # ao voltar para uma sala, o portal abre de novo
    st.rerun()


def enter_room(code: str, token: str) -> None:
    st.query_params.clear()
    st.query_params["room"] = code
    st.query_params["token"] = token
    st.rerun()


def sfx_trigger(names: list[str]) -> None:
    """Agenda sons para o próximo desenho do slot de áudio (id sempre crescente)."""
    FX.sfx_queue(st.session_state, names, time.time())


def sfx_slot() -> None:
    """Iframe invisível que injeta na página o motor de som (Web Audio API) e a
    visualização ampliada das cartas.

    O conteúdo só muda quando há sons novos; o ``id`` crescente garante que
    cada som toque uma única vez, mesmo que o iframe seja recriado.
    """
    data = st.session_state.get("sfx") or {"names": [], "id": 0}
    data["played"] = True
    doc = FX.sound_script(data["names"], data["id"], bool(st.session_state.get("muted")))
    with st.container(key="sfx"):
        if hasattr(st, "iframe"):
            st.iframe(doc, height=1, width=1)
        else:  # Streamlit mais antigo
            import streamlit.components.v1 as components

            components.html(doc, height=0)


def music_slot(mode: str) -> None:
    """Música de fundo: trilha "home" na tela inicial, "game" na sala/partida (crossfade).
    O iframe só muda quando (trilha, mudo) muda; o motor no ``window.parent`` não duplica."""
    state = (mode, bool(st.session_state.get("muted")))
    st.session_state["music_state"] = state
    with st.container(key="musicslot"):
        doc = MU.music_script(*state)
        if hasattr(st, "iframe"):
            st.iframe(doc, height=1, width=1)
        else:  # Streamlit mais antigo
            import streamlit.components.v1 as components

            components.html(doc, height=0)


def tension_slot(level: int) -> None:
    """Reta final da partida para a música do jogo (iframe só muda quando o nível muda)."""
    st.session_state["music_tension"] = level
    with st.container(key="musictension"):
        doc = MU.tension_script(level)
        if hasattr(st, "iframe"):
            st.iframe(doc, height=1, width=1)
        else:  # Streamlit mais antigo
            import streamlit.components.v1 as components

            components.html(doc, height=0)


# =========================================================================== contas

SESSION_COOKIE = "uno_sess"


def auth_configured() -> bool:
    """Login com Google só aparece se ``[auth]`` (com ``[auth.google]``) estiver nos secrets."""
    try:
        auth = st.secrets.get("auth")
        return bool(auth and auth.get("redirect_uri") and auth.get("cookie_secret") and auth.get("google"))
    except Exception:  # sem secrets.toml
        return False


def google_user() -> dict | None:
    if not auth_configured():
        return None
    try:
        if st.user.get("is_logged_in"):
            return dict(st.user)
    except Exception:
        pass
    return None


def account() -> dict | None:
    return st.session_state.get("account")


def set_account(acc: dict | None, token: str | None = None) -> None:
    ss = st.session_state
    if acc is None:
        for k in ("account", "sess_token"):
            ss.pop(k, None)
        return
    ss["account"] = acc
    ss["my_name"] = acc["name"]
    if acc.get("avatar"):
        ss["my_avatar"] = acc["avatar"]
    if token:
        ss["sess_token"] = token


def resolve_account() -> None:
    """Uma vez por sessão do navegador: Google (cookie do Streamlit) ou o cookie ``uno_sess``."""
    ss = st.session_state
    if ss.get("account") or ss.get("auth_checked"):
        return
    ss["auth_checked"] = True
    be = backend()
    try:
        gu = google_user()
        if gu and gu.get("sub"):
            set_account(AC.google_account(be, gu["sub"], gu.get("name", ""), gu.get("email", "")))
            return
        token = ""
        try:
            token = st.context.cookies.get(SESSION_COOKIE, "") or ""
        except Exception:
            token = ""
        if token and token != ss.get("dead_token"):
            acc = AC.session_account(be, token)
            if acc:
                set_account(acc, token)
            else:
                ss["cookie_op"] = ("clear", "")
    except Exception as exc:  # conta nunca derruba o jogo
        flash(f"Não consegui verificar sua conta: {exc}")


def cookie_slot() -> None:
    """Grava/apaga o cookie da sessão no navegador (JS na própria página)."""
    op = st.session_state.pop("cookie_op", None)
    if not op:
        return
    kind, token = op
    # window.parent: funciona no documento principal e também dentro de um iframe
    doc = "(function(){var w;try{w=window.parent.document?window.parent:window}catch(e){w=window}"
    if kind == "set":
        js = (doc + f"w.document.cookie='{SESSION_COOKIE}={token}; path=/; max-age={AC.SESSION_SECONDS}; SameSite=Lax'"
              "+(w.location.protocol==='https:'?'; Secure':'');})();")
    else:
        js = doc + f"w.document.cookie='{SESSION_COOKIE}=; path=/; max-age=0; SameSite=Lax';}})();"
    with st.container(key="cookiejar"):
        st.html(f"<script>{js}</script>", unsafe_allow_javascript=True)


def do_login(acc: dict, remember: bool = True) -> None:
    token = AC.create_session(backend(), acc["key"]) if remember else None
    set_account(acc, token)
    st.session_state.pop("guest", None)
    if token:
        st.session_state["cookie_op"] = ("set", token)
    flash(f"Olá, {acc['name']}!")


def do_logout() -> None:
    ss = st.session_state
    acc = account()
    token = ss.get("sess_token")
    try:
        AC.logout(backend(), token)
    except Exception:
        pass
    ss["dead_token"] = token or ""
    set_account(None)
    ss["cookie_op"] = ("clear", "")
    ss["auth_checked"] = True
    if acc and acc.get("kind") == "google" and auth_configured():
        st.logout()  # apaga o cookie do Streamlit e recarrega
    st.rerun()


def auth_panel(invited: str) -> None:
    """Entrar | Criar conta | Esqueci a senha, Google e "Jogar como convidado"."""
    _, mid, _ = st.columns([1, 2, 1])
    with mid:
        if invited:
            st.info(f"Convite para a sala {invited}: entre na sua conta ou jogue como convidado.")
        with st.container(border=True, key="auth_box"):
            st.markdown("### Sua conta")
            mode = st.segmented_control("Opção", ["Entrar", "Criar conta", "Esqueci a senha"], default="Entrar",
                                        key="auth_mode", label_visibility="collapsed", width="stretch") or "Entrar"
            be = backend()
            today = __import__("datetime").date.today()
            birth_kw = dict(value=None, min_value=today.replace(year=today.year - 110), max_value=today,
                            format="DD/MM/YYYY")
            if mode == "Entrar":
                with st.form("login_form", border=False):
                    user = st.text_input("Usuário", max_chars=R.MAX_NAME, key="login_user")
                    pw = st.text_input("Senha", type="password", key="login_pw")
                    ok = st.form_submit_button("Entrar", type="primary", width="stretch", key="login_submit")
                if ok:
                    try:
                        do_login(AC.login(be, user, pw))
                        st.rerun()
                    except E.GameError as exc:
                        st.error(str(exc))
            elif mode == "Criar conta":
                with st.form("signup_form", border=False):
                    user = st.text_input("Usuário", max_chars=R.MAX_NAME, key="signup_user",
                                         help="É também o seu nome nas salas e no ranking.")
                    birth = st.date_input("Data de nascimento", key="signup_birth",
                                          help="Usada para redefinir a senha se você esquecer.", **birth_kw)
                    pw = st.text_input("Senha (mínimo 6)", type="password", key="signup_pw")
                    pw2 = st.text_input("Confirmar senha", type="password", key="signup_pw2")
                    ok = st.form_submit_button("Criar conta", type="primary", width="stretch", key="signup_submit")
                if ok:
                    try:
                        if birth is None:
                            raise AC.AccountError("Informe a data de nascimento.")
                        acc = AC.register(be, user, birth, pw, pw2)
                        do_login(acc)
                        flash(f"Conta criada. Idade: {AC.age(birth)} anos.")
                        st.rerun()
                    except E.GameError as exc:
                        st.error(str(exc))
            else:
                with st.form("reset_form", border=False):
                    user = st.text_input("Usuário", max_chars=R.MAX_NAME, key="reset_user")
                    birth = st.date_input("Data de nascimento", key="reset_birth", **birth_kw)
                    pw = st.text_input("Nova senha (mínimo 6)", type="password", key="reset_pw")
                    pw2 = st.text_input("Confirmar nova senha", type="password", key="reset_pw2")
                    ok = st.form_submit_button("Trocar senha", type="primary", width="stretch", key="reset_submit")
                if ok:
                    try:
                        acc = AC.reset_password(be, user, birth.isoformat() if birth else "", pw, pw2)
                        do_login(acc)
                        flash("Senha trocada.")
                        st.rerun()
                    except E.GameError as exc:
                        st.error(str(exc))
            st.markdown('<div class="auth-or">ou</div>', unsafe_allow_html=True)
            if auth_configured():
                st.button("Entrar com Google", key="google_login", on_click=st.login, args=("google",),
                          width="stretch")
            else:
                st.button("Entrar com Google", key="google_login", disabled=True, width="stretch",
                          help="O login com Google ainda não foi configurado neste servidor.")
            if st.button("Jogar como convidado", key="guest_btn", type="tertiary", width="stretch"):
                st.session_state["guest"] = True
                st.rerun()


def account_bar() -> None:
    """No topo: avatar + nome + menu da conta (logado) ou "Entrar" (convidado)."""
    acc = account()
    if acc:
        me = {"avatar": acc.get("avatar") or st.session_state.get("my_avatar"), "name": acc["name"]}
        st.markdown(f'<div class="acct">{V.avatar(me, "", 30)}<span>{V.esc(acc["name"])}</span></div>',
                    unsafe_allow_html=True)
        if acc.get("kind") == "google":
            with st.popover("Nome", key="acct_menu", help="Trocar o nome de exibição"):
                new = st.text_input("Nome de exibição", value=acc["name"], max_chars=R.MAX_NAME, key="acct_name")
                if st.button("Salvar nome", key="acct_save", width="stretch") and new != acc["name"]:
                    try:
                        set_account(AC.update_profile(backend(), acc["key"], name=new))
                        st.rerun()
                    except E.GameError as exc:
                        st.error(str(exc))
        if st.button("Sair", key="logout_btn"):
            do_logout()
    elif st.session_state.get("guest"):
        if st.button("Entrar na conta", key="to_login"):
            st.session_state.pop("guest", None)
            st.rerun()


def remember_seat(code: str, player: dict) -> None:
    acc = account()
    if acc:
        try:
            AC.remember_room(backend(), acc["key"], code, player["token"])
        except Exception:
            pass
        remember_avatar(player["avatar"])


def remember_avatar(avatar: str) -> None:
    """Guarda na conta o personagem escolhido (volta escolhido no próximo login)."""
    acc = account()
    if acc and AV.normalize(avatar) and acc.get("avatar") != AV.normalize(avatar):
        try:
            set_account(AC.update_profile(backend(), acc["key"], avatar=avatar))
        except Exception:
            pass


def forget_seat() -> None:
    acc = account()
    if acc:
        try:
            AC.forget_room(backend(), acc["key"])
        except Exception:
            pass


def active_room_banner() -> None:
    acc = account()
    if not acc:
        return
    try:
        found = AC.active_room(backend(), acc["key"])
    except Exception:
        found = None
    if not found:
        return
    room, player = found
    with st.container(border=True, key="back_box"):
        c1, c2 = st.columns([3, 2], vertical_alignment="center")
        state = "partida em andamento" if room["status"] == "playing" else "na sala de espera"
        c1.markdown(f"**Você tem um lugar na sala {V.esc(R.room_title(room))}** ({state}).")
        if c2.button(f"Voltar para a sala {R.room_title(room)}", key="back_room", type="primary", width="stretch"):
            enter_room(room["code"], player["token"])


# =========================================================================== tela inicial

def invite_code() -> str:
    """Código vindo de um convite (``?sala=``) ou de um link antigo sem token (``?room=``)."""
    qp = st.query_params
    if qp.get("sala"):
        return R.extract_code(qp.get("sala", ""))
    if qp.get("room") and not qp.get("token"):
        return R.extract_code(qp.get("room", ""))
    return ""


def draw_room_name() -> None:
    """Botão "Sortear": põe um habitat no campo (sempre diferente do atual)."""
    st.session_state["create_room_name"] = R.suggest_name(exclude=st.session_state.get("create_room_name"))


def pick_room_name() -> None:
    choice = st.session_state.get("room_chips")
    if choice:
        st.session_state["create_room_name"] = choice
    st.session_state["room_chips"] = None


def my_avatar() -> str:
    """Personagem desta sessão: sorteado uma vez, depois o último escolhido."""
    acc_av = (account() or {}).get("avatar")
    if AV.normalize(st.session_state.get("my_avatar")) is None and AV.normalize(acc_av):
        st.session_state["my_avatar"] = acc_av
    if AV.normalize(st.session_state.get("my_avatar")) is None:
        import random as _r

        st.session_state["my_avatar"] = _r.choice(R.AVATARS)
    return AV.normalize(st.session_state["my_avatar"])


def avatar_picker(key: str, current: str, taken: set[str] | None = None, on_change=None, label: str = "Seu personagem"):
    """Grade de retratos (st.radio estilizado; a imagem de cada opção vem do CSS).
    ``taken`` = personagens de outros jogadores (aparecem esmaecidos)."""
    if AV.normalize(st.session_state.get(key)) is None:
        st.session_state[key] = current
    if taken:
        idx = [i for i, k in enumerate(R.AVATARS, 1) if k in taken]
        rules = ",".join(f'.st-key-{key} [role="radiogroup"] > div:nth-of-type({i})' for i in idx)
        st.markdown(f"<style>{rules}{{opacity:.28;filter:grayscale(.9);pointer-events:none}}</style>",
                    unsafe_allow_html=True)
    return st.radio(label, R.AVATARS, key=key, horizontal=True, format_func=AV.short_name,
                    on_change=on_change, width="stretch")


def home() -> None:
    st.markdown(V.logo_html(), unsafe_allow_html=True)
    if st.query_params.get("token"):
        st.warning("Esse link de reconexão não vale mais. Crie uma sala nova ou entre com um código.")
    invited = invite_code()
    acc = account()
    if not acc and not st.session_state.get("guest"):
        auth_panel(invited)
        return
    active_room_banner()
    name_default = st.session_state.get("my_name", "")
    ss_default("create_room_name", "")
    chips = _chip_options()
    # com convite (?sala=CODIGO) o "Entrar" vem primeiro e já preenchido
    left, right = st.columns(2, gap="large")
    join_col, create_col = (left, right) if invited else (right, left)
    with create_col:
        with st.container(border=True, key="create_box"):
            st.markdown("### Criar sala")
            if acc:
                name = acc["name"]
                st.markdown(f'<div class="playing-as">Jogando como <b>{V.esc(name)}</b></div>', unsafe_allow_html=True)
            else:
                name = st.text_input("Seu nome", value=name_default, max_chars=R.MAX_NAME, key="create_name",
                                     placeholder="Seu nome")
            cavatar = avatar_picker("avpick_create", my_avatar())
            c1, c2 = st.columns([3, 1], vertical_alignment="bottom", gap="small")
            room_name = c1.text_input("Nome da sala", max_chars=R.MAX_ROOM_NAME, key="create_room_name",
                                      placeholder=f"Ex.: {chips[0]}")
            c2.button("Sortear", key="draw_room", on_click=draw_room_name, width="stretch")
            st.pills("Sugestões", chips, key="room_chips", on_change=pick_room_name, label_visibility="collapsed")
            bots = st.slider("Bots", 0, E.MAX_PLAYERS - 1, 0, key="create_bots")
            ok = st.button("Criar sala", type="primary", width="stretch", key="create_submit")
        if ok:
            create_room(name, 0, bots, room_name, cavatar)
    with join_col:
        with st.container(key="join_box_invited" if invited else "join_box"):
            with st.form("join_form", border=True):
                st.markdown("### Entrar numa sala")
                c1, c2 = st.columns([3, 1], vertical_alignment="bottom", gap="small")
                code = c1.text_input("Código da sala", value=invited, max_chars=200, key="join_code",
                                     placeholder="5 letras ou link")
                c2.markdown(V.paste_button(".st-key-join_code input"), unsafe_allow_html=True)
                if acc:
                    jname = acc["name"]
                    st.markdown(f'<div class="playing-as">Jogando como <b>{V.esc(jname)}</b></div>',
                                unsafe_allow_html=True)
                else:
                    jname = st.text_input("Seu nome", value=name_default, max_chars=R.MAX_NAME, key="join_name",
                                          placeholder="Seu nome")
                javatar = avatar_picker("avpick_join", my_avatar())
                ok2 = st.form_submit_button("Entrar", type="primary", width="stretch", key="join_submit")
        if ok2:
            join_room(code, jname, javatar)


def _chip_options() -> list[str]:
    """4 habitats sorteados uma vez por sessão (sugestões clicáveis)."""
    if "room_chip_options" not in st.session_state:
        import random as _r

        st.session_state["room_chip_options"] = _r.sample(R.HABITATS, 4)
    return st.session_state["room_chip_options"]


def create_room(name: str, target: int, bots: int, room_name: str = "", avatar: str | None = None) -> None:
    try:
        name = R.clean_name(name)
    except E.GameError as exc:
        st.error(str(exc))
        return
    room_name = R.clean_room_name(room_name)
    if not room_name:  # o app nunca escolhe o nome sozinho
        st.error("Digite um nome para a sala ou clique em Sortear.")
        return
    be = backend()
    if hasattr(be, "cleanup"):
        be.cleanup()
    for _ in range(30):
        code = R.new_code()
        room, host = R.new_room(code, name, name=room_name, avatar=avatar,
                                account=(account() or {}).get("key"))
        R.set_target(room, host["id"], target)
        for _ in range(int(bots)):
            R.add_bot(room, host["id"])
        if be.create_room(code, room):
            st.session_state["my_name"] = name
            st.session_state["my_avatar"] = host["avatar"]
            flash(f"Sala {R.room_title(room)} criada.")
            remember_seat(code, host)
            be.heartbeat(code, host["id"], time.time())
            enter_room(code, host["token"])
            return
    st.error("Não consegui gerar um código livre. Tente de novo.")


def join_room(code: str, name: str, avatar: str | None = None) -> None:
    code = R.extract_code(code)  # aceita código com espaços, minúsculas ou o link inteiro
    if len(code) != R.CODE_LENGTH:
        st.error("O código tem 5 letras.")
        return
    try:
        name = R.clean_name(name)
    except E.GameError as exc:
        st.error(str(exc))
        return
    try:
        acc_key = (account() or {}).get("key")
        _, player = backend().transact(code, lambda r: R.join_room(r, name, avatar, acc_key))
    except RoomNotFound:
        st.error("Sala não encontrada. Confira o código.")
        return
    except E.GameError as exc:
        st.error(str(exc))
        return
    st.session_state["my_name"] = name
    st.session_state["my_avatar"] = player["avatar"]
    if avatar and AV.normalize(avatar) != player["avatar"]:
        # o personagem pedido já estava na sala: avisa (no lobby) qual ficou e que dá para trocar
        st.session_state[f"avatar_notice_{code}"] = (
            f"{AV.full_name(avatar)} já estava com outro jogador. Você ficou com {AV.full_name(player['avatar'])}"
            " — clique em Trocar, ao lado do seu nome, para escolher outro.")
    remember_seat(code, player)
    joined = backend().get_room(code)
    flash(f"Você entrou em {R.room_title(joined) if joined else code}.")
    backend().heartbeat(code, player["id"], time.time())
    enter_room(code, player["token"])


# =========================================================================== sala (atualização ao vivo)

def poll_seconds() -> float:
    return float(os.environ.get("UNO_POLL", backend().poll_seconds))


@st.fragment(run_every=poll_seconds())
def room_view(code: str, token: str) -> None:
    be = backend()
    show_flash()
    room = be.get_room(code)
    if room is None:
        st.error(f"A sala {code} não existe mais.")
        if st.button("Voltar ao início", key="gone_home"):
            go_home()
        return
    me = R.player_by_token(room, token)
    if me is None:
        st.error("Seu lugar nesta sala não foi encontrado (talvez você tenha sido removido).")
        if st.button("Voltar ao início", key="gone_home2"):
            go_home()
        return
    me_id = me["id"]
    now = time.time()

    # --- presença (heartbeat a cada ~4 s)
    hb_key = f"hb_{code}"
    if now - st.session_state.get(hb_key, 0) > 4:
        be.heartbeat(code, me_id, now)
        st.session_state[hb_key] = now
    presence = dict(be.presence(code))
    presence[me_id] = now
    online = {pid for pid, ts in presence.items() if now - ts <= R.OFFLINE_AFTER}

    room = maintenance(code, room, me, presence, now)
    room_arrivals(code, room, me_id, now)
    tension_slot(MU.tension_level(room.get("game") if room["status"] == "playing" else None, room["players"]))
    if room["status"] == "lobby":
        st.session_state[f"seen_{code}"] = {"gid": None, "seq": 0}
        lobby_view(code, room, me, online)
        fx_slots(now)
    else:
        game_view(code, room, me, online, now)


def room_arrivals(code: str, room: dict, me_id: str, now: float) -> None:
    """Portal ao entrar na sala + anúncio quando alguém chega ou vai embora.

    Compara a lista de jogadores do último desenho (em ``st.session_state``)
    com a atual; cada chegada/saída tem uma chave própria e toca uma vez só.
    """
    ss = st.session_state
    FX.fx_push(ss, f"portal:{code}", FX.portal_html(code, f"portal:{code}", R.room_title(room)), now,
               FX.FX_SECONDS["portal"], slot="portal", sounds=["portal"])
    rkey = f"roster_{code}"
    cur = FX.roster(room)
    joined, left = FX.roster_diff(ss.get(rkey), cur, me_id)
    ss[rkey] = cur
    for pid, name in joined:
        key = f"arrive:{code}:{pid}"
        FX.fx_push(ss, key, FX.arrival_html(name, key), now, FX.FX_SECONDS["arrive"], slot="herald", sounds=["arrive"])
    for pid, name in left:
        key = f"depart:{code}:{pid}"
        FX.fx_push(ss, key, FX.departure_html(name, key), now, FX.FX_SECONDS["depart"], slot="herald", sounds=["depart"])


def fx_slots(now: float) -> None:
    """Desenha as sobreposições ativas (o HTML não muda até expirar: não reinicia)."""
    for slot in ("portal", "fx", "herald"):
        with st.container(key=f"{slot}slot"):
            st.markdown(FX.fx_current(st.session_state, slot, now) or "<span></span>", unsafe_allow_html=True)
    sfx_slot()


def resume(state: dict, pid: str) -> None:
    if not R.resume_control(state, pid):
        raise NoChange()


def maintenance(code: str, room: dict, me: dict, presence: dict, now: float) -> dict:
    """Tarefas que qualquer cliente conectado pode fazer (sempre revalidadas na transação)."""
    # voltou depois de cair: retoma o controle (uma vez por sessão)
    rkey = f"resumed_{code}"
    if room["status"] == "playing" and not st.session_state.get(rkey):
        st.session_state[rkey] = True
        if me.get("autopilot") and not me.get("left"):
            res = transact(code, lambda r: resume(r, me["id"]))
            if res:
                room = res[0]

    # um passo de bot (ou piloto automático), se estiver na hora
    pid = R.bot_due(room, now)
    if pid:
        def step(state):
            if not R.run_bot(state, pid):
                raise NoChange()
        res = transact(code, step)
        if res:
            room = res[0]

    # jogador humano sumido há muito tempo e ninguém fez nada: bot assume
    game = room.get("game")
    if room["status"] == "playing" and game and game["status"] == "playing":
        actor = E.whose_action(game)
        p = R.find_player(room, actor)
        if p and not R.automated(p) and now - max(presence.get(actor, 0), room.get("last_action_at", 0)) > R.AUTO_TAKEOVER:
            def take(state):
                if not R.auto_takeover(state, presence, now):
                    raise NoChange()
            res = transact(code, take)
            if res:
                room = res[0]

    # estatísticas da partida que acabou (só um cliente consegue "reivindicar")
    if room.get("stats_pending"):
        def claim(state):
            gid = (state.get("game") or {}).get("gid") or "?"
            done = state.setdefault("stats_recorded", [])
            if not state.get("stats_pending") or gid in done:
                raise NoChange()
            state["stats_pending"] = False      # só um cliente "reivindica" a partida
            done.append(gid)
            del done[:-20]
            return R.stats_entries(state), f"{code}-{gid}"
        res = transact(code, claim)
        if res:
            room, (entries, game_id) = res
            try:
                backend().record_stats(entries, game_id=game_id)
            except Exception as exc:  # estatística nunca derruba o jogo
                flash(f"Não consegui salvar o ranking: {exc}")
    return room


def reconnect_box(code: str, me: dict) -> None:
    link = f"{base_url()}?room={code}&token={me['token']}"
    with st.expander("Link de reconexão (guarde!)"):
        st.caption("Use para voltar ao seu lugar. Não compartilhe.")
        st.code(link, language=None, wrap_lines=True)
        st.caption("Convite para amigos:")
        st.code(invite_link(code), language=None, wrap_lines=True)


def invite_link(code: str) -> str:
    return f"{base_url()}?sala={code}"


# --------------------------------------------------------------------------- lobby

def lobby_view(code: str, room: dict, me: dict, online: set[str]) -> None:
    is_host = room["host"] == me["id"]
    st.markdown(V.room_header(room, invite_link(code)), unsafe_allow_html=True)
    left, right = st.columns([3, 2], gap="large")
    with left:
        st.markdown(f"### Jogadores ({len(room['players'])}/{E.MAX_PLAYERS})")
        notice = st.session_state.get(f"avatar_notice_{code}")
        if notice:
            st.info(notice)
        for p in room["players"]:
            if p["bot"]:
                dot, tag = "bot", "bot"
            else:
                dot, tag = ("on", "online") if p["id"] in online else ("off", "offline")
            crown = f' {icon("crown", 16, "ico-crown", "Anfitrião")}' if p["id"] == room["host"] else ""
            you = " (você)" if p["id"] == me["id"] else ""
            c1, c2 = st.container(key=f"lprow_{p['id']}").columns([5, 2], vertical_alignment="center")
            char = V.esc(AV.full_name(p.get("avatar"))) if AV.normalize(p.get("avatar")) else ""
            c1.markdown(
                f'<div class="lobby-player">{V.avatar(p, dot)}'
                f'<div><b>{V.esc(p["name"])}</b>{you}{crown}<div class="tag">{char + " · " if char else ""}{tag}</div></div></div>',
                unsafe_allow_html=True)
            if p["id"] == me["id"]:
                with c2:
                    my_avatar_popover(code, room, me)
            elif is_host:
                if c2.button("Remover", key=f"rm_{p['id']}", help=f"Remover {p['name']}", width="stretch"):
                    transact(code, lambda r, t=p["id"]: R.remove_player(r, me["id"], t))
                    refresh()
        st.markdown(f'<div class="small-muted">Meta: {TARGET_LABELS[room["settings"]["target"]]}</div>',
                    unsafe_allow_html=True)
    with right:
        if is_host:
            st.markdown("### Você é o anfitrião")
            target = st.selectbox("Como vencer", R.TARGET_OPTIONS, format_func=lambda t: TARGET_LABELS[t],
                                  index=R.TARGET_OPTIONS.index(room["settings"]["target"]), key="lobby_target")
            if target != room["settings"]["target"]:
                transact(code, lambda r: R.set_target(r, me["id"], target))
                refresh()
            full = len(room["players"]) >= E.MAX_PLAYERS
            if st.button("Adicionar bot", key="add_bot", disabled=full, width="stretch"):
                transact(code, lambda r: R.add_bot(r, me["id"]))
                refresh()
            few = len(room["players"]) < E.MIN_PLAYERS
            if st.button("Começar partida!", key="start", type="primary", disabled=few, width="stretch"):
                if transact(code, lambda r: R.start_game(r, me["id"])):
                    refresh()
            if few:
                st.caption("Precisa de pelo menos 2 jogadores.")
        else:
            st.markdown("### Aguardando o anfitrião…")
        if st.button("Sair da sala", key="leave_lobby", width="stretch"):
            transact(code, lambda r: R.leave_room(r, me["id"]))
            forget_seat()
            go_home()
        reconnect_box(code, me)
        log = room.get("lobby_log", [])[-8:]
        st.markdown('<div class="log">' + "".join(f"<div>{V.esc(x)}</div>" for x in reversed(log)) + "</div>",
                    unsafe_allow_html=True)


def my_avatar_popover(code: str, room: dict, me: dict) -> None:
    """Botão "Trocar" ao lado do meu nome: abre a grade de personagens (só no lobby)."""
    key = f"avpick_lobby_{code}"
    current = AV.normalize(me.get("avatar")) or my_avatar()
    st.session_state[key] = current  # sempre igual ao que está gravado na sala

    def change() -> None:
        choice = st.session_state.get(key)

        def swap(state: dict) -> None:
            if not R.set_avatar(state, me["id"], choice):
                raise NoChange()
        res = transact(code, swap)
        if res:
            st.session_state["my_avatar"] = choice
            st.session_state.pop(f"avatar_notice_{code}", None)
            remember_avatar(choice)

    with st.popover("Trocar", key=f"avpop_{code}", help="Trocar seu personagem", width="stretch"):
        avatar_picker(key, current, AV.used_in(room["players"], exclude_pid=me["id"]), on_change=change,
                      label="Escolha seu personagem")
        st.caption("Os apagados já foram escolhidos por outros jogadores.")


# --------------------------------------------------------------------------- partida

def sort_hand(hand: list[dict]) -> list[dict]:
    return sorted(hand, key=lambda c: (COLOR_ORDER[c["color"]], KIND_ORDER[c["kind"]], c.get("value") or 0, c["id"]))


def track_events(code: str, game: dict, me_id: str) -> tuple[list[dict], bool]:
    """Eventos novos desde o último desenho nesta sessão (para sons/efeitos)."""
    key = f"seen_{code}"
    gid = game.get("gid")
    rec = st.session_state.get(key)
    if rec is None:
        rec = {"gid": gid, "seq": game["seq"]}   # recém-chegado/recarregou: não repete efeitos antigos
    elif rec.get("gid") != gid:
        rec = {"gid": gid, "seq": 0}             # partida nova começou com a gente olhando
    new = [ev for ev in game["events"] if ev["seq"] > rec["seq"]]
    rec["seq"] = game["seq"]
    st.session_state[key] = rec
    tkey = f"myturn_{code}"
    mine = E.whose_action(game) == me_id
    started = mine and not st.session_state.get(tkey, False)
    st.session_state[tkey] = mine
    return new, started


def effects_slot(code: str, gid: str, new_events: list[dict], turn_started: bool, names: dict, me_id: str,
                 now: float, events: list[dict] | None = None) -> None:
    """Escolhe o efeito mais importante entre os eventos novos e toca uma vez (chave = sala+partida+seq).

    Se houve uma jogada, o duelo de biomas toca primeiro (para todos na sala, inclusive
    jogadas de bots) e o efeito da carta especial entra logo depois, na fila do slot."""
    queued = False
    last_play = next((ev for ev in reversed(new_events) if ev["type"] == "play"), None)
    duel = DU.duel_for(events or new_events, last_play) if last_play else None
    if duel:
        queued = FX.fx_push(st.session_state, f"duel:{code}:{gid}:{duel['seq']}", DU.duel_html(duel), now,
                            DU.DUEL_SECONDS, slot="fx", sounds=[duel["sound"]])
    if new_events or turn_started:
        sounds = FX.sounds_for(new_events, turn_started, me_id)
        ev = FX.pick_fx(new_events)
        if ev is None and turn_started:
            ev = {"type": "turn", "seq": int(now * 1000)}
        html = FX.fx_html(ev, names, me_id) if ev is not None else ""
        if duel and duel["wild"] and ev is not None and ev["type"] == "wild":
            html = ""  # a invasão da cor escolhida já é o efeito do coringa
        key = f"ev:{code}:{gid}:{ev['type']}:{ev['seq']}" if ev is not None else f"snd:{code}:{gid}:{now}"
        if queued and sounds and sounds[0] == "play":
            sounds = sounds[1:]  # o som do bioma já marca a jogada
        FX.fx_push(st.session_state, key, html, now, FX.fx_seconds_for(ev, me_id) if ev else None,
                   slot="fx", sounds=sounds, after=queued)


def game_view(code: str, room: dict, me: dict, online: set[str], now: float) -> None:
    game = room["game"]
    me_id = me["id"]
    is_host = room["host"] == me_id
    by_id = {p["id"]: p for p in room["players"]}
    names = {p["id"]: p["name"] for p in room["players"]}
    new_events, turn_started = track_events(code, game, me_id)
    effects_slot(code, str(game.get("gid")), new_events, turn_started, names, me_id, now, game["events"])

    actor = E.whose_action(game)
    my_action = actor == me_id
    pending = game.get("pending")
    new_types = {ev["type"] for ev in new_events}

    main, side = st.columns([3, 1], gap="medium")
    with main:
        with st.container(key="table"):
            st.markdown(V.seats_html(room, me_id, online), unsafe_allow_html=True)
            last_play = next((ev for ev in reversed(new_events) if ev["type"] == "play"), None)
            discard = V.discard_html(game, animate=last_play is not None,
                                     from_me=bool(last_play and last_play.get("player") == me_id),
                                     seq=game["seq"])
            st.markdown(f'<div class="center">{V.deck_html(game)}{discard}{V.status_html(room, me_id)}</div>',
                        unsafe_allow_html=True)
            if game["status"] == "playing":
                action_bar(code, room, me, my_action, pending)
            else:
                round_result(code, room, me, is_host)
        hand_view(code, game, me, my_action, pending, deal="deal" in new_types)
    with side:
        side_panel(code, room, me, by_id, online, is_host)
    fx_slots(now)  # no fim: as camadas são fixas e não empurram o layout


def act(code: str, me_id: str, action: str, **kw) -> None:
    transact(code, lambda r: R.act(r, me_id, action, **kw))
    st.session_state.pop("pending_wild", None)
    refresh()


def color_buttons(prefix: str = "pick") -> str | None:
    cols = st.columns(4)
    chosen = None
    for col, color in zip(cols, E.COLORS):
        b = BIOMES[color]
        if col.button(b["name"], key=f"{prefix}_{color}", width="stretch"):
            chosen = color
    return chosen


def set_auto(code: str, me_id: str, on: bool) -> None:
    try:
        transact(code, lambda r: R.set_auto_play(r, me_id, on, confirmed=True))
    except E.GameError as exc:
        st.error(str(exc))
        return
    st.session_state.pop("auto_confirm", None)
    if on:
        st.session_state["auto_warned"] = True
    refresh()


def auto_control(code: str, me: dict) -> bool:
    """"Jogar automático": aviso na primeira vez; ligado, selo "Automático" com "Desligar"."""
    ss = st.session_state
    me_id = me["id"]
    if me.get("auto_play"):
        with st.container(key="auto_on_box", horizontal=True, vertical_alignment="center", gap="small"):
            st.markdown(f'<div class="auto-badge">{icon("spirit", 15)} Automático</div>', unsafe_allow_html=True,
                        width="content")
            if st.button("Desligar", key="auto_off", type="tertiary"):
                set_auto(code, me_id, False)
        return True
    if ss.get("auto_confirm"):
        with st.container(border=True, key="auto_warn"):
            st.markdown(f'<div class="hint">{V.esc(R.AUTO_WARNING)}</div>', unsafe_allow_html=True)
            c1, c2 = st.columns(2)
            if c1.button("Ligar mesmo assim", key="auto_yes", type="primary", width="stretch"):
                set_auto(code, me_id, True)
            if c2.button("Cancelar", key="auto_no", width="stretch"):
                ss.pop("auto_confirm", None)
                refresh()
        return False
    if st.button("Jogar automático", key="auto_btn", type="tertiary",
                 help="Na sua vez, o app joga por você com a IA dos bots."):
        if ss.get("auto_warned"):
            set_auto(code, me_id, True)
        else:
            ss["auto_confirm"] = True
            refresh()
    return False


def action_bar(code: str, room: dict, me: dict, my_action: bool, pending: dict | None) -> None:
    game = room["game"]
    me_id = me["id"]
    names = {p["id"]: p["name"] for p in room["players"]}
    if not me.get("autopilot") and auto_control(code, me):
        if my_action:
            st.markdown('<div class="hint">O app está jogando por você...</div>', unsafe_allow_html=True)
        return

    # denunciar quem esqueceu o UNO! (qualquer um, a qualquer momento da janela)
    vul = game.get("vulnerable")
    if vul and vul != me_id:
        if st.button(f"Denunciar {names.get(vul, '?')}: esqueceu o UNO! (+2)", key=f"den_{vul}",
                     width="stretch"):
            act(code, me_id, "denounce", target=vul)

    if E.can_shout_uno(game, me_id):
        if st.button("UNO!", key="btn_uno", width="stretch"):
            act(code, me_id, "uno")

    if not my_action:
        if me.get("autopilot"):
            st.markdown(f'<div class="hint">{icon("spirit", 16)} Um bot está jogando por você.</div>',
                        unsafe_allow_html=True)
            if st.button("Retomar o controle", key="resume", width="stretch"):
                transact(code, lambda r: resume(r, me_id))
                refresh()
        return

    if pending and pending["type"] == "wild4":
        st.markdown(f'<div class="hint">{icon("fire", 16)} {V.esc(names.get(pending["offender"], "?"))} jogou +4 em você. '
                    'Aceite (compra 4) ou desafie: se ele tinha a cor da mesa, ele compra 4; senão, você compra 6.</div>', unsafe_allow_html=True)
        c1, c2 = st.columns(2)
        if c1.button("Aceitar +4", key="btn_accept", width="stretch"):
            act(code, me_id, "accept")
        if c2.button("Desafiar!", key="btn_challenge", type="primary", width="stretch"):
            act(code, me_id, "challenge")
        return
    if pending and pending["type"] == "choose_color":
        st.markdown('<div class="hint">A primeira carta é um Coringa (Iara): escolha a cor inicial.</div>',
                    unsafe_allow_html=True)
        color = color_buttons("pick")
        if color:
            act(code, me_id, "color", color=color)
        return

    wild_id = st.session_state.get("pending_wild")
    if wild_id and any(c["id"] == wild_id for c in game["hands"][me_id]):
        st.markdown(f'<div class="hint">{icon("palette", 16)} Escolha a nova cor para o coringa:</div>',
                    unsafe_allow_html=True)
        color = color_buttons("pick")
        if color:
            act(code, me_id, "play", card_id=wild_id, color=color)
        if st.button("Cancelar", key="cancel_wild"):
            st.session_state.pop("pending_wild", None)
            refresh()
        return

    if pending and pending["type"] == "drawn":
        st.markdown('<div class="hint">Você comprou uma carta que serve! Jogue-a (brilhando na mão) ou passe a vez.</div>',
                    unsafe_allow_html=True)
        if st.button("Passar a vez", key="btn_pass", width="stretch"):
            act(code, me_id, "pass")
        return

    has_play = bool(E.playable_cards(game, me_id))
    hint = "Jogue uma carta que brilha ou compre." if has_play else "Nenhuma carta serve: compre uma."
    st.markdown(f'<div class="hint">{hint}</div>', unsafe_allow_html=True)
    if st.button("Comprar carta", key="btn_draw", type="secondary" if has_play else "primary",
                 width="stretch"):
        act(code, me_id, "draw")


def hand_view(code: str, game: dict, me: dict, my_action: bool, pending: dict | None, deal: bool) -> None:
    me_id = me["id"]
    hand = sort_hand(game["hands"].get(me_id, []))
    playable = {c["id"] for c in E.playable_cards(game, me_id)}
    drawn_id = pending["card_id"] if pending and pending["type"] == "drawn" and my_action else None
    turn = " turn" if my_action and game["status"] == "playing" else ""
    glow = ('<style>.st-key-hand{box-shadow: inset 0 0 40px #ff9d2e33, 0 0 0 1px #e2b04e99, 0 0 30px #ff9d2e44;'
            'animation: hand-glow 1.8s ease-in-out infinite}@keyframes hand-glow{50%{box-shadow: inset 0 0 60px #ff9d2e55,'
            ' 0 0 0 1px #f6d98a, 0 0 40px #ff9d2e77}}@media (prefers-reduced-motion: reduce){.st-key-hand{animation:none}}</style>'
            if turn else "")
    st.markdown(
        f'{glow}<div class="mybar{turn}">{V.avatar(me, "on", 46)}'
        f'<div><div class="nm">{V.esc(me["name"])} (você)</div>'
        f'<div class="sub">{len(hand)} carta{"s" if len(hand) != 1 else ""} na mão · '
        f'{game["scores"].get(me_id, 0)} pts · {E.hand_points(hand)} pts na mão</div></div></div>',
        unsafe_allow_html=True)
    if not hand:
        return
    with st.container(key="hand", horizontal=True, gap="small"):
        for i, card in enumerate(hand):
            cid = card["id"]
            can = cid in playable
            cls = "playable" if can else ("dim" if my_action else "")
            pill = ""
            if cid == drawn_id:
                cls += " drawn"
                pill = "comprada"
            if deal:
                cls += " deal"
            with st.container(key=f"hc_{cid}", width=104):
                st.markdown(V.card_html(card, cls, f"--d:{i * 0.07:.2f}s", pill), unsafe_allow_html=True)
                if st.button(E.card_label(card), key=f"play_{cid}", disabled=not can):
                    if card["kind"] in E.WILD_KINDS:
                        st.session_state["pending_wild"] = cid
                        refresh()
                    act(code, me_id, "play", card_id=cid)


def round_result(code: str, room: dict, me: dict, is_host: bool) -> None:
    game = room["game"]
    winner = game["round_winner"]
    names = {p["id"]: p["name"] for p in room["players"]}
    over = game["status"] == "game_over"
    title = f"{icon('trophy', 22)} Fim de jogo!" if over else f"{icon('torch', 22)} Fim da rodada {game['round']}"
    rows = []
    for pid in game["players"]:
        left = E.hand_points(game["hands"][pid])
        cls = " win" if pid == winner else ""
        extra = f"+{game['round_points']}" if pid == winner else f"{len(game['hands'][pid])} cartas ({left} pts)"
        rows.append(f'<div class="result-row{cls}"><span>{V.esc(names.get(pid, pid))}</span>'
                    f'<span>{extra} · total {game["scores"][pid]}</span></div>')
    st.markdown(f'<div class="panel"><h3>{title}</h3><p><b>{V.esc(names.get(winner, "?"))}</b> bateu e levou '
                f'{game["round_points"]} pontos.</p>{"".join(rows)}</div>', unsafe_allow_html=True)
    if is_host:
        if over:
            if st.button("Nova partida (voltar à sala)", key="to_lobby", type="primary", width="stretch"):
                transact(code, lambda r: R.back_to_lobby(r, me["id"]))
                refresh()
        elif st.button("Próxima rodada", key="next_round", type="primary", width="stretch"):
            transact(code, lambda r: R.next_round(r, me["id"]))
            refresh()
    else:
        st.caption("Aguardando o anfitrião continuar…")


def side_panel(code: str, room: dict, me: dict, by_id: dict, online: set[str], is_host: bool) -> None:
    game = room["game"]
    me_id = me["id"]
    st.markdown(f'<div class="small-muted">Sala <b>{V.esc(R.room_title(room))}</b> · código {code} · '
                f'{len(game["players"])} jogadores</div>',
                unsafe_allow_html=True)
    actor = E.whose_action(game)
    if is_host and actor and actor != me_id and game["status"] == "playing":
        p = by_id.get(actor)
        if p and not R.automated(p) and actor not in online:
            st.warning(f"{p['name']} está offline e é a vez dele.")
            if st.button(f"Pular a vez de {p['name']}", key="host_skip", width="stretch"):
                transact(code, lambda r: R.host_skip(r, me_id, actor))
                refresh()
            if st.button(f"Bot joga por {p['name']}", key="host_bot", width="stretch"):
                transact(code, lambda r: R.host_autopilot(r, me_id, actor, True))
                refresh()
    st.markdown("#### Placar")
    rows = "".join(
        f'<tr><td>{V.avatar(by_id[pid], "", 26)}{V.esc(by_id[pid]["name"])}</td>'
        f'<td>{len(game["hands"][pid])} carta{"s" if len(game["hands"][pid]) != 1 else ""}</td>'
        f'<td><b>{game["scores"][pid]}</b></td></tr>' for pid in game["players"] if pid in by_id)
    st.markdown(f'<table class="scores">{rows}</table>', unsafe_allow_html=True)
    st.markdown("#### Acontecimentos")
    st.markdown(V.log_html(game["events"]), unsafe_allow_html=True)
    reconnect_box(code, me)
    if st.button("Sair da partida", key="leave_game", width="stretch"):
        transact(code, lambda r: R.leave_room(r, me_id))
        forget_seat()
        go_home()


# =========================================================================== outras abas

def bestiary_tab() -> None:
    st.markdown("### Bestiário")
    st.caption("Passe o mouse ou segure o dedo sobre uma carta para ampliar.")
    st.markdown(V.bestiary_html(), unsafe_allow_html=True)
    with st.expander("Composição do baralho (108 cartas)"):
        rows = [f"| {n} | {CHARACTERS[NUMBER_CHARS[n]]['name']} | {1 if n == 0 else 2} por cor ({4 if n == 0 else 8} no total) |"
                for n in range(10)]
        acts = {"skip": "Pular", "reverse": "Inverter", "draw2": "+2", "wild": "Coringa", "wild4": "Coringa +4"}
        for kind, label in acts.items():
            qty = "2 por cor (8 no total)" if kind in E.ACTION_KINDS else "4 no total"
            rows.append(f"| {label} | {CHARACTERS[KIND_CHARS[kind]]['name']} | {qty} |")
        st.markdown("| Carta | Personagem | Quantidade |\n|---|---|---|\n" + "\n".join(rows))


# fragmento próprio: a mesa só redesenha o fragmento dela, então sem isto o ranking
# ficava parado até a página inteira recarregar (ex.: não mostrava a partida que acabou)
@st.fragment(run_every=float(os.environ.get("UNO_RANK_POLL", 15)))
def ranking_tab() -> None:
    st.markdown("### Ranking")
    be = backend()
    try:
        rows = be.ranking()
    except Exception as exc:
        st.error(f"Não consegui carregar o ranking: {exc}")
        return
    me_name = st.session_state.get("my_name", "")
    me_key = (account() or {}).get("key") or (R.name_key(me_name) if me_name else "")
    st.markdown(V.ranking_html(rows, me_key, online=be.name in ("rtdb", "firebase")), unsafe_allow_html=True)
    st.caption("Só jogadores humanos. Atualizado ao fim de cada partida.")


def top_bar() -> None:
    """Controles de som (sempre visíveis) e informação do armazenamento."""
    be = backend()
    with st.container(key="topbar", horizontal=True, vertical_alignment="center", gap="small"):
        st.markdown(f'<div class="topline">{icon("torch", 16)} <span>Uno Folclóuno</span>'
                    f'<span class="where"> · armazenamento: {backend_label(be)}</span></div>',
                    unsafe_allow_html=True, width="stretch")
        st.toggle("Silenciar sons", key="muted", help="Os navegadores só liberam áudio depois do primeiro clique na página.")
        clicked = st.button("Testar som", key="test_sound")
        account_bar()
    if clicked:
        sfx_trigger(["wild", "uno"])
    warn = backend_warning()
    if warn:
        st.warning(warn)


# =========================================================================== principal

def main() -> None:
    st.markdown(CSS, unsafe_allow_html=True)
    st.markdown(ambient_html(), unsafe_allow_html=True)
    ss_default("muted", False)
    resolve_account()
    top_bar()
    cookie_slot()
    code = R.normalize_code(st.query_params.get("room", ""))
    token = st.query_params.get("token", "")
    in_room = False
    if code and token:
        room = backend().get_room(code)
        in_room = bool(room and R.player_by_token(room, token))
    music_slot("game" if in_room else "home")
    play, beasts, rank, rules = st.tabs(["Jogar", "Bestiário", "Ranking", "Regras"])
    with play:
        if in_room:
            room_view(code, token)
        else:
            show_flash()
            home()
            fx_slots(time.time())
    with beasts:
        bestiary_tab()
    with rank:
        ranking_tab()
    with rules:
        st.markdown(V.RULES_MD)


main()
