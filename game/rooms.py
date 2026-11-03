"""Regras de sala (lobby, anfitrião, bots, reconexão) — funções puras sobre o
estado da sala. O armazenamento (arquivo/Firestore) chama estas funções dentro
de uma transação, então cada jogada é validada do lado do servidor."""

from __future__ import annotations

import os
import random
import secrets
import string
import time
import re
import unicodedata

from . import avatars as A
from . import bots as B
from . import engine as E

CODE_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ"  # sem I e O (evita confusão)
CODE_LENGTH = 5
MAX_NAME = 18
BOT_DELAY = float(os.environ.get("UNO_BOT_DELAY", "1.3"))  # segundos entre jogadas de bot
OFFLINE_AFTER = 20       # segundos sem heartbeat = offline
AUTO_TAKEOVER = 60       # sem anfitrião por perto: bot assume quem sumiu há 60 s
TARGET_OPTIONS = [0, 100, 200, 500]
# Sugestões de NOME DE SALA: habitats dos personagens do folclore (o usuário sorteia ou escolhe)
HABITATS = ["Mata Atlântica", "Rio Negro", "Pantanal", "Cerrado", "Caatinga",
            "Igarapé", "Várzea", "Serra do Mar", "Encontro das Águas", "Pampa"]
# avatares = personagens do folclore (medalhões SVG desenhados em ui/icons.py, sem emoji)
AVATARS = A.KEYS
AVATAR_TAKEN = "Esse personagem já foi escolhido."


class RoomError(E.GameError):
    pass


def new_code(rng: random.Random | None = None) -> str:
    rng = rng or random.SystemRandom()
    return "".join(rng.choice(CODE_ALPHABET) for _ in range(CODE_LENGTH))


def normalize_code(code: str) -> str:
    return "".join(ch for ch in (code or "").upper() if ch in string.ascii_uppercase)[:CODE_LENGTH]


def extract_code(text: str) -> str:
    """Aceita o código colado de qualquer jeito: 'kxptz', ' KX PTZ ', ou o link inteiro
    do convite (``...?sala=KXPTZ`` / ``...?room=KXPTZ``)."""
    text = text or ""
    m = re.search(r"[?&#](?:sala|room)=([A-Za-z\s]+)", text)
    if m:
        text = m.group(1)
    elif "://" in text or "/" in text:
        text = text.rstrip("/").rsplit("/", 1)[-1]
    return normalize_code(text)


def suggest_name(rng: random.Random | None = None, exclude: str | None = None) -> str:
    """Um habitat da lista (sugestão de nome de sala), diferente de ``exclude``."""
    options = [h for h in HABITATS if h != exclude] or HABITATS
    return (rng or random).choice(options)


MAX_ROOM_NAME = 24
_PICTO = re.compile("[\U0001F000-\U0001FAFF\u2600-\u27BF\u2B00-\u2BFF\u2300-\u23FF\uFE0F\u200D]")


def clean_room_name(name: str | None) -> str:
    """Nome da sala: sem caracteres de controle/marcação, espaços normalizados, até 24 caracteres."""
    name = "".join(ch for ch in (name or "") if ch.isprintable() and ch not in "<>{}[]\\`"
                   and not _PICTO.match(ch))
    return " ".join(name.split())[:MAX_ROOM_NAME].strip()


def room_title(room: dict) -> str:
    """Nome para exibir (salas antigas, sem nome, mostram o código)."""
    return room.get("name") or room.get("code") or "Sala"


def clean_name(name: str) -> str:
    name = " ".join((name or "").split())[:MAX_NAME]
    if not name:
        raise RoomError("Digite um nome.")
    return name


def name_key(name: str) -> str:
    """Chave normalizada para estatísticas (sem acento, minúsculas)."""
    base = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode().lower()
    key = "".join(ch if ch.isalnum() else "-" for ch in base).strip("-")
    return key or "jogador"


def _check_avatar(avatar: str | None) -> str | None:
    if avatar is None or avatar == "":
        return None
    key = A.normalize(avatar)
    if key is None:
        raise RoomError("Personagem inválido.")
    return key


def _new_player(name: str, bot: bool, room: dict, avatar: str | None = None, account: str | None = None) -> dict:
    """Novo jogador com o personagem pedido; se ele já estiver em uso (ou não vier
    nenhum), fica com um livre sorteado — quem chamou compara e avisa o jogador."""
    avatar = A.pick_free(room["players"], _check_avatar(avatar))
    extra = {"account": account} if account else {}
    return {
        **extra,
        "id": "p" + secrets.token_hex(4),
        "token": secrets.token_urlsafe(16),
        "name": name,
        "bot": bot,
        "avatar": avatar,
        "autopilot": False,
        "joined_at": time.time(),
    }


def new_room(code: str, host_name: str, now: float | None = None, name: str | None = None,
             rng: random.Random | None = None, avatar: str | None = None,
             account: str | None = None) -> tuple[dict, dict]:
    now = time.time() if now is None else now
    room = {
        "code": code,
        "name": clean_room_name(name) or suggest_name(rng),
        "version": 0,
        "created_at": now,
        "updated_at": now,
        "last_action_at": now,
        "status": "lobby",          # lobby | playing
        "host": None,
        "settings": {"target": 0},
        "players": [],
        "game": None,
        "games_played": 0,
        "stats_pending": False,
        "lobby_log": [],
    }
    host = _new_player(clean_name(host_name), False, room, avatar, account)
    room["players"].append(host)
    room["host"] = host["id"]
    room["lobby_log"].append(f"{host['name']} criou a sala.")
    return room, host


def find_player(room: dict, pid: str | None = None, token: str | None = None) -> dict | None:
    for p in room["players"]:
        if pid is not None and p["id"] == pid:
            return p
        if token is not None and p["token"] == token:
            return p
    return None


def player_by_token(room: dict, token: str) -> dict | None:
    if not token:
        return None
    return find_player(room, token=token)


def _require_host(room: dict, pid: str) -> None:
    if room["host"] != pid:
        raise RoomError("Só o anfitrião pode fazer isso.")


def _require_lobby(room: dict) -> None:
    if room["status"] != "lobby":
        raise RoomError("A partida já começou.")


def _check_capacity(room: dict) -> None:
    if len(room["players"]) >= E.MAX_PLAYERS:
        raise RoomError(f"Sala cheia (máximo {E.MAX_PLAYERS} jogadores).")


def join_room(room: dict, name: str, avatar: str | None = None, account: str | None = None) -> dict:
    """Entra na sala. Se ``avatar`` já estiver com outro jogador, recebe um livre
    (compare ``player["avatar"]`` com o pedido para avisar). Com ``account``, quem já
    tem lugar na sala volta para o mesmo lugar (mesmo id e token), mesmo com a partida em andamento."""
    if account:
        mine = next((p for p in room["players"] if p.get("account") == account and not p.get("left")), None)
        if mine:
            return mine
    _require_lobby(room)
    name = clean_name(name)
    _check_avatar(avatar)
    _check_capacity(room)
    if any(p["name"].casefold() == name.casefold() for p in room["players"]):
        raise RoomError("Já existe alguém com esse nome na sala. Escolha outro (ou use seu link de reconexão).")
    player = _new_player(name, False, room, avatar, account)
    room["players"].append(player)
    room["lobby_log"].append(f"{name} entrou na sala.")
    return player


def add_bot(room: dict, pid: str) -> dict:
    _require_host(room, pid)
    _require_lobby(room)
    _check_capacity(room)
    used = {p["name"] for p in room["players"]}
    name = next((n for n in B.BOT_NAMES if n not in used), f"Bot {len(room['players']) + 1}")
    bot = _new_player(name, True, room)
    room["players"].append(bot)
    room["lobby_log"].append(f"{name} sentou à mesa.")
    return bot


def remove_player(room: dict, pid: str, target: str) -> None:
    _require_host(room, pid)
    _require_lobby(room)
    if target == pid:
        raise RoomError("O anfitrião não pode remover a si mesmo.")
    p = find_player(room, target)
    if not p:
        raise RoomError("Jogador não encontrado.")
    room["players"].remove(p)
    room["lobby_log"].append(f"{p['name']} foi removido.")


def leave_room(room: dict, pid: str) -> None:
    """Saída voluntária. No lobby, a cadeira é liberada; em jogo, um bot assume."""
    p = find_player(room, pid)
    if not p:
        return
    if room["status"] == "lobby":
        room["players"].remove(p)
        room["lobby_log"].append(f"{p['name']} saiu da sala.")
    else:
        p["autopilot"] = True
        p["left"] = True
        _game_event(room, "left", pid, f"{p['name']} saiu — um bot assume a vez dele.")
    humans = [x for x in room["players"] if not x["bot"] and not x.get("left")]
    if room["host"] == pid and humans:
        room["host"] = humans[0]["id"]
        msg = f"{humans[0]['name']} agora é o anfitrião."
        if room["status"] == "lobby":
            room["lobby_log"].append(msg)
        else:
            _game_event(room, "host", humans[0]["id"], msg)


def set_avatar(room: dict, pid: str, avatar: str) -> bool:
    """Troca o personagem do jogador (só no lobby). Retorna False se já era esse."""
    _require_lobby(room)
    me = find_player(room, pid)
    if not me:
        raise RoomError("Você não está nesta sala.")
    key = _check_avatar(avatar)
    if key is None:
        raise RoomError("Personagem inválido.")
    if A.normalize(me.get("avatar")) == key:
        return False
    if key in A.used_in(room["players"], exclude_pid=pid):
        raise RoomError(AVATAR_TAKEN)
    me["avatar"] = key
    room["lobby_log"].append(f"{me['name']} agora é {A.full_name(key)}.")
    return True


def set_target(room: dict, pid: str, target: int) -> None:
    _require_host(room, pid)
    _require_lobby(room)
    if target not in TARGET_OPTIONS:
        raise RoomError("Meta de pontos inválida.")
    room["settings"]["target"] = target


def start_game(room: dict, pid: str, rng: random.Random | None = None, now: float | None = None) -> None:
    _require_host(room, pid)
    _require_lobby(room)
    if len(room["players"]) < E.MIN_PLAYERS:
        raise RoomError("São necessários pelo menos 2 jogadores (adicione um bot!).")
    ids = [p["id"] for p in room["players"]]
    names = {p["id"]: p["name"] for p in room["players"]}
    room["game"] = E.new_game(ids, names, room["settings"]["target"], rng)
    room["game"]["gid"] = secrets.token_hex(4)  # identifica a partida (efeitos/sons no cliente)
    room["status"] = "playing"
    room["stats_pending"] = False
    room["last_action_at"] = time.time() if now is None else now


def _game_event(room: dict, etype: str, pid: str | None, text: str) -> None:
    if room.get("game"):
        E._event(room["game"], etype, pid, text)


def _touch(room: dict, now: float | None) -> None:
    room["last_action_at"] = time.time() if now is None else now


def act(room: dict, pid: str, action: str, rng: random.Random | None = None,
        now: float | None = None, **kw) -> None:
    """Aplica a ação de um jogador humano, validando tudo."""
    if room["status"] != "playing" or not room.get("game"):
        raise RoomError("Nenhuma partida em andamento.")
    me = find_player(room, pid)
    if not me:
        raise RoomError("Você não está nesta sala.")
    if me.get("autopilot") and not me.get("left"):
        me["autopilot"] = False  # voltou: retoma o controle
    game = room["game"]
    before = game["status"]
    if action == "play":
        E.play_card(game, pid, kw["card_id"], kw.get("color"), rng)
    elif action == "draw":
        E.draw_action(game, pid, rng)
    elif action == "pass":
        E.pass_turn(game, pid)
    elif action == "uno":
        E.shout_uno(game, pid)
    elif action == "denounce":
        E.denounce(game, pid, kw["target"], rng)
    elif action == "challenge":
        E.respond_wild4(game, pid, True, rng)
    elif action == "accept":
        E.respond_wild4(game, pid, False, rng)
    elif action == "color":
        E.choose_start_color(game, pid, kw["color"])
    else:
        raise RoomError("Ação desconhecida.")
    _touch(room, now)
    _after(room, before)


def _after(room: dict, before: str) -> None:
    game = room["game"]
    if before == "playing" and game["status"] == "game_over":
        for p in room["players"]:
            p.pop("auto_play", None)  # o jogar automático desliga sozinho no fim
        room["stats_pending"] = True
        room["games_played"] = room.get("games_played", 0) + 1


def is_offline(presence: dict, pid: str, now: float | None = None) -> bool:
    now = time.time() if now is None else now
    return now - presence.get(pid, 0) > OFFLINE_AFTER


def automated(player: dict) -> bool:
    return bool(player["bot"] or player.get("autopilot") or player.get("auto_play"))


AUTO_WARNING = "As jogadas automáticas são imprecisas. Para jogar melhor, jogue você mesmo."


def set_auto_play(room: dict, pid: str, on: bool, confirmed: bool = False) -> bool:
    """"Jogar automático" (escolha do próprio jogador): na vez dele, a IA dos bots joga,
    pelo mesmo caminho validado (``run_bot``). Ligar exige ter confirmado o aviso.
    Desliga sozinho no fim da partida. Retorna False se nada mudou."""
    p = find_player(room, pid)
    if not p or p["bot"] or p.get("left"):
        raise RoomError("Jogador inválido.")
    if on:
        if not confirmed:
            raise RoomError(AUTO_WARNING)
        game = room.get("game")
        if room["status"] != "playing" or not game or game["status"] == "game_over":
            raise RoomError("Nenhuma partida em andamento.")
    if bool(p.get("auto_play")) == bool(on):
        return False
    p["auto_play"] = bool(on)
    _game_event(room, "auto_play", pid,
                f"{p['name']} ligou o jogar automático." if on else f"{p['name']} desligou o jogar automático.")
    return True


def bot_due(room: dict, now: float | None = None) -> str | None:
    """Retorna o id do bot/piloto automático que deve jogar agora (ou None)."""
    now = time.time() if now is None else now
    if room["status"] != "playing" or not room.get("game"):
        return None
    game = room["game"]
    if game["status"] != "playing":
        return None
    if now - room.get("last_action_at", 0) < BOT_DELAY:
        return None
    actor = E.whose_action(game)
    p = find_player(room, actor)
    if p and automated(p):
        return actor
    # bots também denunciam humanos distraídos
    vul = game.get("vulnerable")
    if vul and now - room.get("last_action_at", 0) > BOT_DELAY * 3:
        for q in room["players"]:
            if q["bot"] and q["id"] != vul:
                return q["id"]
    return None


def run_bot(room: dict, pid: str, rng: random.Random | None = None, now: float | None = None) -> bool:
    """Executa um passo de bot se ainda for devido (revalidado dentro da transação)."""
    if bot_due(room, now) != pid:
        return False
    game = room["game"]
    before = game["status"]
    actor = E.whose_action(game)
    if actor == pid:
        p = find_player(room, pid) or {}
        careful = bool(p.get("auto_play")) and not p["bot"]
        B.bot_step(game, pid, rng, careful=careful)
        if careful:  # a partida registra que houve jogadas automáticas (o ranking conta normalmente)
            moves = game.setdefault("auto_moves", {})
            moves[pid] = moves.get(pid, 0) + 1
    else:
        vul = game.get("vulnerable")
        if vul and vul != pid and (rng or random).random() < 0.5:
            E.denounce(game, pid, vul, rng)
    _touch(room, now)
    _after(room, before)
    return True


def host_skip(room: dict, pid: str, target: str, rng: random.Random | None = None, now=None) -> None:
    _require_host(room, pid)
    game = room.get("game")
    if not game:
        raise RoomError("Nenhuma partida em andamento.")
    E.skip_player(game, target)
    _touch(room, now)


def host_autopilot(room: dict, pid: str, target: str, on: bool = True, now=None) -> None:
    _require_host(room, pid)
    p = find_player(room, target)
    if not p or p["bot"]:
        raise RoomError("Jogador inválido.")
    p["autopilot"] = on
    _game_event(room, "autopilot", target,
                f"Um bot está jogando por {p['name']} até ele voltar." if on else f"{p['name']} retomou o controle.")
    _touch(room, now)


def auto_takeover(room: dict, presence: dict, now: float | None = None) -> str | None:
    """Se quem precisa agir é humano e sumiu há mais de AUTO_TAKEOVER segundos,
    um bot assume a vez dele (evita a mesa travar se o anfitrião também sumiu)."""
    now = time.time() if now is None else now
    game = room.get("game")
    if room["status"] != "playing" or not game or game["status"] != "playing":
        return None
    actor = E.whose_action(game)
    p = find_player(room, actor)
    if not p or automated(p):
        return None
    last_seen = max(presence.get(actor, 0), room.get("last_action_at", 0))
    if now - last_seen <= AUTO_TAKEOVER:
        return None
    p["autopilot"] = True
    _game_event(room, "autopilot", actor, f"{p['name']} sumiu: um bot joga por ele até ele voltar.")
    _touch(room, now)
    return actor


def resume_control(room: dict, pid: str) -> bool:
    p = find_player(room, pid)
    if p and p.get("autopilot") and not p.get("left"):
        p["autopilot"] = False
        _game_event(room, "autopilot", pid, f"{p['name']} voltou e retomou o controle.")
        return True
    return False


def next_round(room: dict, pid: str, rng: random.Random | None = None, now=None) -> None:
    _require_host(room, pid)
    E.next_round(room["game"], rng)
    _touch(room, now)


def back_to_lobby(room: dict, pid: str) -> None:
    _require_host(room, pid)
    if room.get("game") and room["game"]["status"] == "playing":
        raise RoomError("A partida ainda está em andamento.")
    room["status"] = "lobby"
    room["players"] = [p for p in room["players"] if not p.get("left")]
    for p in room["players"]:
        p["autopilot"] = False
        p.pop("auto_play", None)
    room["last_game"] = room.get("game")
    room["game"] = None
    room["lobby_log"].append("Nova partida! Aguardando o anfitrião começar.")


def stats_entries(room: dict) -> list[tuple[str, str, dict]]:
    """(chave, nome, incrementos) para cada humano da partida que acabou."""
    game = room.get("game") or {}
    out = []
    for p in room["players"]:
        if p["bot"] or p["id"] not in game.get("stats", {}):
            continue
        s = dict(game["stats"][p["id"]])
        inc = {
            "games": 1,
            "wins": 1 if game.get("winner") == p["id"] else 0,
            "points": game["scores"].get(p["id"], 0),
            **s,
        }
        # com conta, a chave do ranking é a da conta (para login por senha ela é igual
        # à chave antiga por nome, então as estatísticas antigas continuam somando)
        out.append((p.get("account") or name_key(p["name"]), p["name"], inc))
    return out
