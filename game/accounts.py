"""Contas de jogador: cadastro, login, redefinição de senha, sessões e vínculo com salas.

Tudo passa pelos documentos genéricos do armazenamento (``doc_get``/``doc_update``,
mesma interface no arquivo local, no Realtime Database e no Firestore)::

    users/{chave}     conta. Chave = nome de login normalizado (sem acento,
                      minúsculas; igual à chave antiga do ranking) ou ``g_{sub}``
                      para contas Google.
    sessions/{hash}   sessão de login por senha: só o SHA-256 do token fica salvo.
    limits/{tipo:chave}  tentativas erradas na janela de 15 minutos.

Senhas: PBKDF2-HMAC-SHA256 com 240 mil iterações e salt aleatório por conta;
comparação em tempo constante (``hmac.compare_digest``). Nada em texto puro.
"""

from __future__ import annotations

import datetime as _dt
import hashlib
import hmac
import secrets
import time
import unicodedata

from . import avatars as AV
from .engine import GameError
from .rooms import MAX_NAME, clean_name, find_player

PBKDF2_ITERATIONS = 240_000
MIN_PASSWORD = 6
SESSION_DAYS = 30
SESSION_SECONDS = SESSION_DAYS * 24 * 3600
MAX_FAILS = 5
FAIL_WINDOW = 15 * 60

LOGIN_ERROR = "Usuário ou senha incorretos."
RESET_ERROR = "Usuário ou data não conferem."
LIMIT_ERROR = "Muitas tentativas. Espere 15 minutos e tente de novo."


class AccountError(GameError):
    pass


# =========================================================================== senha

def hash_password(password: str, salt: bytes | None = None, iterations: int = PBKDF2_ITERATIONS) -> dict:
    salt = salt or secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, iterations)
    return {"algo": "pbkdf2_sha256", "iter": iterations, "salt": salt.hex(), "hash": digest.hex()}


def verify_password(password: str, record: dict | None) -> bool:
    if not record or record.get("algo") != "pbkdf2_sha256":
        return False
    digest = hashlib.pbkdf2_hmac("sha256", (password or "").encode("utf-8"),
                                 bytes.fromhex(record["salt"]), int(record["iter"]))
    return hmac.compare_digest(digest.hex(), record["hash"])


def check_new_password(password: str, confirm: str) -> None:
    if len(password or "") < MIN_PASSWORD:
        raise AccountError(f"A senha precisa ter pelo menos {MIN_PASSWORD} caracteres.")
    if password != confirm:
        raise AccountError("As senhas não são iguais.")


# =========================================================================== dados

def user_key(username: str) -> str:
    """Chave do login (sem diferenciar maiúsculas/acentos); "" se não sobrar letra/número."""
    # mesma normalização de ``rooms.name_key`` (chave do ranking), mas sem o "jogador" de reserva
    base = unicodedata.normalize("NFKD", " ".join((username or "").split())).encode("ascii", "ignore").decode().lower()
    return "".join(ch if ch.isalnum() else "-" for ch in base).strip("-")


def clean_username(username: str) -> str:
    try:
        name = clean_name(username)
    except GameError:
        raise AccountError("Digite um nome de usuário.") from None
    if len(user_key(name).replace("-", "")) < 3:
        raise AccountError("O nome de usuário precisa ter pelo menos 3 letras ou números.")
    return name


def parse_birth(value) -> _dt.date:
    if isinstance(value, _dt.datetime):
        value = value.date()
    if isinstance(value, _dt.date):
        d = value
    else:
        try:
            d = _dt.date.fromisoformat(str(value))
        except ValueError:
            raise AccountError("Data de nascimento inválida.") from None
    today = _dt.date.today()
    if d > today or d.year < today.year - 120:
        raise AccountError("Data de nascimento inválida.")
    return d


def age(birth, today: _dt.date | None = None) -> int:
    b = parse_birth(birth)
    t = today or _dt.date.today()
    return t.year - b.year - ((t.month, t.day) < (b.month, b.day))


def public(user: dict) -> dict:
    """O que a interface pode ver (nunca o hash da senha nem a data)."""
    return {"key": user["key"], "name": user["name"], "kind": user.get("kind", "password"),
            "avatar": user.get("avatar"), "email": user.get("email", "")}


# =========================================================================== limite de tentativas

def _limit_key(kind: str, key: str) -> str:
    return f"{kind}-{key}"


def _check_limit(be, kind: str, key: str, now: float) -> None:
    doc = be.doc_get("limits", _limit_key(kind, key)) or {}
    fails = [t for t in doc.get("fails", []) if now - t < FAIL_WINDOW]
    if len(fails) >= MAX_FAILS:
        raise AccountError(LIMIT_ERROR)


def _register_fail(be, kind: str, key: str, now: float) -> None:
    def fn(cur):
        fails = [t for t in (cur or {}).get("fails", []) if now - t < FAIL_WINDOW] + [now]
        return {"fails": fails[-20:]}, None
    be.doc_update("limits", _limit_key(kind, key), fn)


def _clear_fails(be, kind: str, key: str) -> None:
    be.doc_update("limits", _limit_key(kind, key), lambda cur: (None, None))


# =========================================================================== cadastro / login

def register(be, username: str, birth, password: str, confirm: str, now: float | None = None) -> dict:
    now = time.time() if now is None else now
    name = clean_username(username)
    b = parse_birth(birth)
    check_new_password(password, confirm)
    key = user_key(name)
    record = {"key": key, "name": name, "kind": "password", "birth": b.isoformat(),
              "password": hash_password(password), "created_at": now, "pw_changed_at": now}

    def fn(cur):
        if cur is not None:  # dentro da transação: dois cadastros iguais nunca passam
            raise AccountError("Esse nome de usuário já existe. Escolha outro.")
        return record, None

    be.doc_update("users", key, fn)
    return public(record)


def login(be, username: str, password: str, now: float | None = None) -> dict:
    now = time.time() if now is None else now
    key = user_key(username)
    if not key:
        raise AccountError(LOGIN_ERROR)
    _check_limit(be, "login", key, now)
    user = be.doc_get("users", key)
    if not user or user.get("kind") != "password" or not verify_password(password, user.get("password")):
        _register_fail(be, "login", key, now)
        raise AccountError(LOGIN_ERROR)
    _clear_fails(be, "login", key)
    return public(user)


def reset_password(be, username: str, birth, password: str, confirm: str, now: float | None = None) -> dict:
    now = time.time() if now is None else now
    check_new_password(password, confirm)
    key = user_key(username)
    if not key:
        raise AccountError(RESET_ERROR)
    _check_limit(be, "reset", key, now)
    try:
        b = parse_birth(birth).isoformat()
    except AccountError:
        b = ""

    def fn(cur):
        if not cur or cur.get("kind") != "password" or not hmac.compare_digest(cur.get("birth", ""), b):
            return cur, False
        cur = dict(cur)
        cur["password"] = hash_password(password)
        cur["pw_changed_at"] = now  # sessões antigas deixam de valer
        return cur, True

    ok = be.doc_update("users", key, fn)
    if not ok:
        _register_fail(be, "reset", key, now)
        raise AccountError(RESET_ERROR)
    _clear_fails(be, "reset", key)
    _clear_fails(be, "login", key)
    return public(be.doc_get("users", key))


def google_account(be, sub: str, name: str = "", email: str = "", now: float | None = None) -> dict:
    """Conta Google (``g_{sub}``): criada no primeiro login; o nome de exibição é editável."""
    now = time.time() if now is None else now
    if not sub:
        raise AccountError("Login do Google sem identificador.")
    key = "g_" + "".join(ch for ch in str(sub) if ch.isalnum())[:64]
    display = " ".join((name or email.split("@")[0] or "Jogador").split())[:MAX_NAME]

    def fn(cur):
        if cur is not None:
            return cur, cur
        rec = {"key": key, "name": display, "kind": "google", "email": email, "created_at": now}
        return rec, rec

    return public(be.doc_update("users", key, fn))


def get_account(be, key: str) -> dict | None:
    user = be.doc_get("users", key) if key else None
    return public(user) if user else None


def update_profile(be, key: str, name: str | None = None, avatar: str | None = None) -> dict:
    if name is not None:
        name = clean_name(name)
    if avatar is not None and AV.normalize(avatar) is None:
        raise AccountError("Personagem inválido.")

    def fn(cur):
        if cur is None:
            raise AccountError("Conta não encontrada.")
        cur = dict(cur)
        if name is not None:
            if cur.get("kind") != "google":
                raise AccountError("O nome de usuário não pode ser trocado.")
            cur["name"] = name
        if avatar is not None:
            cur["avatar"] = AV.normalize(avatar)
        return cur, cur

    return public(be.doc_update("users", key, fn))


# =========================================================================== sessões

def _token_hash(token: str) -> str:
    return hashlib.sha256((token or "").encode("utf-8")).hexdigest()


def create_session(be, key: str, now: float | None = None, seconds: float = SESSION_SECONDS) -> str:
    now = time.time() if now is None else now
    token = secrets.token_urlsafe(32)
    be.doc_update("sessions", _token_hash(token),
                  lambda cur: ({"user": key, "created": now, "expires": now + seconds}, None))
    return token


def session_account(be, token: str | None, now: float | None = None) -> dict | None:
    """Conta da sessão, ou None (token desconhecido, vencido ou anterior à troca de senha)."""
    if not token or len(token) > 200:
        return None
    now = time.time() if now is None else now
    h = _token_hash(token)
    sess = be.doc_get("sessions", h)
    if not sess:
        return None
    if now >= sess.get("expires", 0):
        be.doc_update("sessions", h, lambda cur: (None, None))
        return None
    user = be.doc_get("users", sess.get("user", ""))
    if not user or sess.get("created", 0) < user.get("pw_changed_at", 0):
        return None
    return public(user)


def logout(be, token: str | None) -> None:
    if token:
        be.doc_update("sessions", _token_hash(token), lambda cur: (None, None))


# =========================================================================== salas da conta

def remember_room(be, key: str, code: str, token: str) -> None:
    """Guarda na conta a última sala (código + token do lugar) para reconectar depois."""
    def fn(cur):
        if cur is None:
            return None, None
        cur = dict(cur)
        cur["room"] = {"code": code, "token": token, "at": time.time()}
        return cur, None
    be.doc_update("users", key, fn)


def forget_room(be, key: str) -> None:
    def fn(cur):
        if cur is None:
            return None, None
        cur = dict(cur)
        cur.pop("room", None)
        return cur, None
    be.doc_update("users", key, fn)


def active_room(be, key: str) -> tuple[dict, dict] | None:
    """(sala, jogador) se a conta ainda tem lugar numa sala que não terminou."""
    user = be.doc_get("users", key) if key else None
    info = (user or {}).get("room")
    if not info:
        return None
    room = be.get_room(info.get("code", ""))
    if not room:
        return None
    player = find_player(room, token=info.get("token"))
    if not player or player.get("left") or player.get("account") not in (None, key):
        return None
    game = room.get("game")
    if room.get("status") == "playing" and game and game.get("status") == "game_over":
        return None
    return room, player
