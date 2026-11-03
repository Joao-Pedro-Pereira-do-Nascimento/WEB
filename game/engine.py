"""Motor puro do Uno Folclóuno.

Todas as funções recebem/alteram um dicionário ``game`` serializável em JSON
(para poder ser salvo em arquivo ou no Firestore) e validam cada jogada do
lado do servidor: só o jogador da vez age, só cartas legais são aceitas.
Nenhuma dependência de Streamlit aqui.
"""

from __future__ import annotations

import random
from collections import Counter

COLORS = ["red", "green", "blue", "yellow"]
COLOR_NAMES = {"red": "Fogo", "green": "Mata", "blue": "Rios", "yellow": "Cerrado", "wild": "Coringa"}
ACTION_KINDS = ["skip", "reverse", "draw2"]
WILD_KINDS = ["wild", "wild4"]
HAND_SIZE = 7
MAX_EVENTS = 60
MIN_PLAYERS = 2
MAX_PLAYERS = 6

STAT_KEYS = [
    "cards_played", "cards_drawn", "uno_shouts", "denounces", "penalties",
    "wild4_played", "action_played",
]


class GameError(Exception):
    """Jogada inválida (mensagem em português para mostrar ao jogador)."""


# --------------------------------------------------------------------------- baralho

def build_deck() -> list[dict]:
    """Baralho oficial de 108 cartas."""
    deck: list[dict] = []
    for color in COLORS:
        c = color[0].upper()
        deck.append({"id": f"{c}-0-a", "color": color, "kind": "number", "value": 0})
        for value in range(1, 10):
            for copy in "ab":
                deck.append({"id": f"{c}-{value}-{copy}", "color": color, "kind": "number", "value": value})
        for kind in ACTION_KINDS:
            for copy in "ab":
                deck.append({"id": f"{c}-{kind}-{copy}", "color": color, "kind": kind, "value": None})
    for kind in WILD_KINDS:
        for copy in "abcd":
            deck.append({"id": f"W-{kind}-{copy}", "color": "wild", "kind": kind, "value": None})
    return deck


def card_points(card: dict) -> int:
    if card["kind"] == "number":
        return int(card["value"])
    if card["kind"] in ACTION_KINDS:
        return 20
    return 50


def card_label(card: dict) -> str:
    """Rótulo curto em português, ex.: 'Fogo 7', 'Mata Pular', 'Coringa +4'."""
    names = {"skip": "Pular", "reverse": "Inverter", "draw2": "+2", "wild": "Coringa", "wild4": "+4"}
    if card["kind"] == "number":
        return f"{COLOR_NAMES[card['color']]} {card['value']}"
    if card["kind"] == "wild":
        return "Coringa"
    if card["kind"] == "wild4":
        return "Coringa +4"
    return f"{COLOR_NAMES[card['color']]} {names[card['kind']]}"


def matches(card: dict, top: dict, current_color: str | None) -> bool:
    """Regra de combinação: cor, número ou símbolo (curingas sempre)."""
    if card["kind"] in WILD_KINDS:
        return True
    if current_color is None:
        return True
    if card["color"] == current_color:
        return True
    if card["kind"] == "number":
        return top["kind"] == "number" and top["value"] == card["value"]
    return card["kind"] == top["kind"]


# --------------------------------------------------------------------------- helpers

def _rng(rng: random.Random | None) -> random.Random:
    return rng if rng is not None else random.Random()


def current_player(game: dict) -> str:
    return game["players"][game["current"]]


def top_card(game: dict) -> dict:
    return game["discard"][-1]


def _step(game: dict, steps: int = 1) -> int:
    n = len(game["players"])
    return (game["current"] + steps * game["direction"]) % n


def next_player_id(game: dict) -> str:
    return game["players"][_step(game, 1)]


def _advance(game: dict, steps: int = 1) -> None:
    game["current"] = _step(game, steps)
    game["turn_started"] = game["seq"] + 1


def _event(game: dict, etype: str, player: str | None = None, text: str = "", **extra) -> dict:
    game["seq"] += 1
    ev = {"seq": game["seq"], "type": etype, "player": player, "text": text}
    ev.update(extra)
    game["events"].append(ev)
    if len(game["events"]) > MAX_EVENTS:
        del game["events"][: len(game["events"]) - MAX_EVENTS]
    return ev


def _stat(game: dict, pid: str, key: str, amount: int = 1) -> None:
    game["stats"].setdefault(pid, {k: 0 for k in STAT_KEYS})
    game["stats"][pid][key] = game["stats"][pid].get(key, 0) + amount


def _name(game: dict, pid: str | None) -> str:
    if pid is None:
        return "?"
    return game.get("names", {}).get(pid, pid)


def _reshuffle(game: dict, rng: random.Random) -> bool:
    if len(game["discard"]) <= 1:
        return False
    top = game["discard"].pop()
    pile = game["discard"]
    rng.shuffle(pile)
    game["deck"] = pile + game["deck"]
    game["discard"] = [top]
    _event(game, "shuffle", None, "O monte acabou: o descarte foi embaralhado e virou o novo monte.")
    return True


def _draw(game: dict, pid: str, count: int, rng: random.Random) -> list[dict]:
    drawn = []
    for _ in range(count):
        if not game["deck"] and not _reshuffle(game, rng):
            break
        card = game["deck"].pop()
        game["hands"][pid].append(card)
        drawn.append(card)
    if drawn:
        _stat(game, pid, "cards_drawn", len(drawn))
        if pid in game["uno_safe"]:
            game["uno_safe"].remove(pid)
    return drawn


def _clear_vulnerable_if_other(game: dict, pid: str) -> None:
    """A janela de denúncia fecha quando outro jogador começa a agir."""
    if game.get("vulnerable") and game["vulnerable"] != pid:
        game["vulnerable"] = None


def _require_playing(game: dict) -> None:
    if game["status"] != "playing":
        raise GameError("A rodada não está em andamento.")


def _require_turn(game: dict, pid: str) -> None:
    _require_playing(game)
    if pid not in game["hands"]:
        raise GameError("Você não está nesta partida.")
    if current_player(game) != pid:
        raise GameError("Não é a sua vez!")


def _find_card(game: dict, pid: str, card_id: str) -> dict:
    for card in game["hands"][pid]:
        if card["id"] == card_id:
            return card
    raise GameError("Essa carta não está na sua mão.")


# --------------------------------------------------------------------------- partida e rodada

def new_game(player_ids: list[str], names: dict[str, str] | None = None,
             target: int = 0, rng: random.Random | None = None) -> dict:
    """Cria uma partida e já distribui a primeira rodada.

    ``target`` = pontos para vencer a partida (0 = rodada única).
    """
    if not MIN_PLAYERS <= len(player_ids) <= MAX_PLAYERS:
        raise GameError(f"São necessários de {MIN_PLAYERS} a {MAX_PLAYERS} jogadores.")
    if len(set(player_ids)) != len(player_ids):
        raise GameError("Jogadores repetidos.")
    game = {
        "players": list(player_ids),
        "names": dict(names or {pid: pid for pid in player_ids}),
        "hands": {},
        "deck": [],
        "discard": [],
        "current": 0,
        "direction": 1,
        "color": None,
        "pending": None,
        "uno_safe": [],
        "vulnerable": None,
        "round": 0,
        "dealer": -1,
        "scores": {pid: 0 for pid in player_ids},
        "target": int(target),
        "status": "playing",
        "round_winner": None,
        "round_points": 0,
        "winner": None,
        "events": [],
        "seq": 0,
        "turn_started": 0,
        "stats": {pid: {k: 0 for k in STAT_KEYS} for pid in player_ids},
    }
    start_round(game, rng)
    return game


def start_round(game: dict, rng: random.Random | None = None) -> None:
    rng = _rng(rng)
    n = len(game["players"])
    game["round"] += 1
    game["dealer"] = (game["dealer"] + 1) % n
    deck = build_deck()
    rng.shuffle(deck)
    game.update({
        "deck": deck, "discard": [], "direction": 1, "color": None, "pending": None,
        "uno_safe": [], "vulnerable": None, "status": "playing",
        "round_winner": None, "round_points": 0,
        "hands": {pid: [] for pid in game["players"]},
    })
    for _ in range(HAND_SIZE):
        for pid in game["players"]:
            game["hands"][pid].append(game["deck"].pop())
    # A primeira carta virada não pode ser +4: volta para o monte.
    while True:
        first = game["deck"].pop()
        if first["kind"] != "wild4":
            break
        game["deck"].insert(rng.randrange(len(game["deck"]) + 1), first)
    game["discard"].append(first)
    _event(game, "deal", None, f"Rodada {game['round']}: {HAND_SIZE} cartas para cada um.", round=game["round"])
    game["current"] = (game["dealer"] + 1) % n
    first_pid = current_player(game)
    _event(game, "flip", None, f"Carta virada: {card_label(first)}.", card=first)
    if first["kind"] == "wild":
        game["pending"] = {"type": "choose_color", "player": first_pid}
    else:
        game["color"] = first["color"]
        if first["kind"] == "skip":
            _event(game, "skip", first_pid, f"{_name(game, first_pid)} perdeu a vez (Saci!).", card=first)
            _advance(game, 1)
        elif first["kind"] == "reverse":
            game["direction"] = -1
            game["current"] = game["dealer"]
            _event(game, "reverse", None, "O sentido foi invertido (Curupira!).", card=first)
        elif first["kind"] == "draw2":
            _draw(game, first_pid, 2, rng)
            _event(game, "draw2", first_pid, f"{_name(game, first_pid)} comprou 2 e perdeu a vez.", card=first, target=first_pid)
            _advance(game, 1)
    game["turn_started"] = game["seq"]


def next_round(game: dict, rng: random.Random | None = None) -> None:
    if game["status"] != "round_over":
        raise GameError("A rodada ainda não terminou.")
    start_round(game, rng)


def whose_action(game: dict) -> str | None:
    """Quem precisa agir agora (jogador da vez, ou alvo de +4 / escolha de cor)."""
    if game["status"] != "playing":
        return None
    pending = game.get("pending")
    if pending and pending["type"] == "wild4":
        return pending["target"]
    if pending and pending["type"] == "choose_color":
        return pending["player"]
    return current_player(game)


def is_playable(game: dict, card: dict) -> bool:
    return matches(card, top_card(game), game["color"])


def playable_cards(game: dict, pid: str) -> list[dict]:
    """Cartas que ``pid`` pode jogar agora (vazio se não for a vez dele)."""
    if game["status"] != "playing" or whose_action(game) != pid or current_player(game) != pid:
        return []
    pending = game.get("pending")
    if pending:
        if pending["type"] == "drawn":
            card = next((c for c in game["hands"][pid] if c["id"] == pending["card_id"]), None)
            return [card] if card and is_playable(game, card) else []
        return []
    return [c for c in game["hands"][pid] if is_playable(game, c)]


# --------------------------------------------------------------------------- ações

def choose_start_color(game: dict, pid: str, color: str) -> None:
    _require_playing(game)
    pending = game.get("pending")
    if not pending or pending["type"] != "choose_color" or pending["player"] != pid:
        raise GameError("Não há cor para escolher agora.")
    if color not in COLORS:
        raise GameError("Cor inválida.")
    game["color"] = color
    game["pending"] = None
    _event(game, "color", pid, f"{_name(game, pid)} escolheu a cor {COLOR_NAMES[color]}.", color=color)


def play_card(game: dict, pid: str, card_id: str, color: str | None = None,
              rng: random.Random | None = None) -> dict:
    rng = _rng(rng)
    _require_turn(game, pid)
    pending = game.get("pending")
    if pending and pending["type"] in ("wild4", "choose_color"):
        raise GameError("Resolva a ação pendente primeiro.")
    card = _find_card(game, pid, card_id)
    if pending and pending["type"] == "drawn" and pending["card_id"] != card_id:
        raise GameError("Depois de comprar, só é possível jogar a carta comprada (ou passar).")
    if not is_playable(game, card):
        raise GameError("Essa carta não combina com a mesa.")
    if card["kind"] in WILD_KINDS:
        if color not in COLORS:
            raise GameError("Escolha uma cor para o coringa.")
    else:
        color = card["color"]

    _clear_vulnerable_if_other(game, pid)
    illegal_wild4 = False
    if card["kind"] == "wild4":
        prev = game["color"]
        illegal_wild4 = any(c["color"] == prev for c in game["hands"][pid] if c["id"] != card_id)

    game["pending"] = None
    game["hands"][pid].remove(card)
    game["discard"].append(card)
    game["color"] = color
    _stat(game, pid, "cards_played")
    if card["kind"] != "number":
        _stat(game, pid, "action_played")
    if card["kind"] == "wild4":
        _stat(game, pid, "wild4_played")
    who = _name(game, pid)
    text = f"{who} jogou {card_label(card)}"
    if card["kind"] in WILD_KINDS:
        text += f" e escolheu {COLOR_NAMES[color]}"
    _event(game, "play", pid, text + ".", card=card, color=color)

    hand_left = len(game["hands"][pid])
    if hand_left == 1:
        if pid not in game["uno_safe"]:
            game["vulnerable"] = pid  # esqueceu o UNO! — pode ser denunciado
    else:
        if pid in game["uno_safe"]:
            game["uno_safe"].remove(pid)
        if game.get("vulnerable") == pid:
            game["vulnerable"] = None

    nxt = next_player_id(game)
    n = len(game["players"])
    kind = card["kind"]
    if hand_left == 0:
        # Efeitos de compra ainda valem na última carta (contam pontos).
        if kind == "draw2":
            _draw(game, nxt, 2, rng)
            _event(game, "draw2", nxt, f"{_name(game, nxt)} comprou 2 cartas (Cuca!).", card=card, target=nxt)
        elif kind == "wild4":
            _draw(game, nxt, 4, rng)
            _event(game, "wild4", nxt, f"{_name(game, nxt)} comprou 4 cartas (Mula sem Cabeça!).", card=card, target=nxt)
        _finish_round(game, pid)
        return card

    if kind == "number" or kind == "wild":
        if kind == "wild":
            _event(game, "wild", pid, f"Iara encantou a mesa: cor {COLOR_NAMES[color]}.", color=color)
        _advance(game, 1)
    elif kind == "skip":
        _event(game, "skip", nxt, f"{_name(game, nxt)} perdeu a vez (Saci!).", card=card, target=nxt)
        _advance(game, 2)
    elif kind == "reverse":
        game["direction"] *= -1
        if n == 2:
            _event(game, "reverse", pid, f"Curupira inverteu tudo: {who} joga de novo!", card=card)
            _advance(game, 2)
        else:
            _event(game, "reverse", pid, "O sentido do jogo foi invertido (Curupira!).", card=card)
            _advance(game, 1)
    elif kind == "draw2":
        _draw(game, nxt, 2, rng)
        _event(game, "draw2", nxt, f"{_name(game, nxt)} comprou 2 e perdeu a vez (Cuca!).", card=card, target=nxt)
        _advance(game, 2)
    elif kind == "wild4":
        _advance(game, 1)
        game["pending"] = {"type": "wild4", "target": nxt, "offender": pid, "illegal": illegal_wild4}
        _event(game, "wild4_wait", nxt, f"{_name(game, nxt)} deve aceitar o +4 ou desafiar.", target=nxt)
    return card


def draw_action(game: dict, pid: str, rng: random.Random | None = None) -> dict | None:
    """Jogador da vez compra 1 carta. Se for jogável, pode jogá-la; senão a vez passa."""
    rng = _rng(rng)
    _require_turn(game, pid)
    if game.get("pending"):
        raise GameError("Você já comprou nesta vez — jogue a carta comprada ou passe." if game["pending"]["type"] == "drawn" else "Resolva a ação pendente primeiro.")
    _clear_vulnerable_if_other(game, pid)
    drawn = _draw(game, pid, 1, rng)
    if not drawn:
        _event(game, "pass", pid, f"{_name(game, pid)} não tinha o que comprar e passou.")
        _advance(game, 1)
        return None
    card = drawn[0]
    _event(game, "draw", pid, f"{_name(game, pid)} comprou uma carta.")
    if is_playable(game, card):
        game["pending"] = {"type": "drawn", "player": pid, "card_id": card["id"]}
    else:
        _event(game, "pass", pid, f"{_name(game, pid)} passou a vez.")
        _advance(game, 1)
    return card


def pass_turn(game: dict, pid: str) -> None:
    _require_turn(game, pid)
    pending = game.get("pending")
    if not pending or pending["type"] != "drawn":
        raise GameError("Só dá para passar depois de comprar uma carta.")
    game["pending"] = None
    _event(game, "pass", pid, f"{_name(game, pid)} passou a vez.")
    _advance(game, 1)


def respond_wild4(game: dict, pid: str, challenge: bool, rng: random.Random | None = None) -> bool:
    """Resposta ao +4. Retorna True se o desafio foi bem-sucedido."""
    rng = _rng(rng)
    _require_playing(game)
    pending = game.get("pending")
    if not pending or pending["type"] != "wild4" or pending["target"] != pid:
        raise GameError("Não há +4 para você responder.")
    _clear_vulnerable_if_other(game, pid)
    offender = pending["offender"]
    game["pending"] = None
    if not challenge:
        _draw(game, pid, 4, rng)
        _event(game, "wild4", pid, f"{_name(game, pid)} comprou 4 cartas e perdeu a vez (Mula sem Cabeça!).", target=pid)
        _advance(game, 1)
        return False
    if pending["illegal"]:
        _draw(game, offender, 4, rng)
        _stat(game, offender, "penalties")
        _event(game, "challenge_ok", pid,
               f"Desafio certeiro! {_name(game, offender)} tinha a cor da mesa e comprou 4.", target=offender)
        # o desafiante joga normalmente (a vez continua com ele)
        game["turn_started"] = game["seq"]
        return True
    _draw(game, pid, 6, rng)
    _event(game, "challenge_fail", pid,
           f"Desafio falhou! {_name(game, pid)} comprou 6 cartas e perdeu a vez.", target=pid)
    _advance(game, 1)
    return False


def can_shout_uno(game: dict, pid: str) -> bool:
    if game["status"] != "playing" or pid not in game["hands"]:
        return False
    size = len(game["hands"][pid])
    if size == 1:
        return game.get("vulnerable") == pid
    if size == 2:
        return current_player(game) == pid and pid not in game["uno_safe"] and whose_action(game) == pid
    return False


def shout_uno(game: dict, pid: str) -> None:
    _require_playing(game)
    if not can_shout_uno(game, pid):
        raise GameError("Só dá para gritar UNO! com 2 cartas na sua vez (antes de jogar) ou logo após ficar com 1.")
    if len(game["hands"][pid]) == 1:
        game["vulnerable"] = None
    game["uno_safe"].append(pid)
    _stat(game, pid, "uno_shouts")
    _event(game, "uno", pid, f"{_name(game, pid)} gritou UNO!")


def denounce(game: dict, accuser: str, target: str, rng: random.Random | None = None) -> None:
    """Qualquer outro jogador denuncia quem ficou com 1 carta sem gritar UNO: +2."""
    rng = _rng(rng)
    _require_playing(game)
    if accuser not in game["hands"]:
        raise GameError("Você não está nesta partida.")
    if accuser == target:
        raise GameError("Você não pode denunciar a si mesmo.")
    if game.get("vulnerable") != target:
        raise GameError("Tarde demais (ou ele já gritou UNO!).")
    game["vulnerable"] = None
    _draw(game, target, 2, rng)
    _stat(game, accuser, "denounces")
    _stat(game, target, "penalties")
    _event(game, "denounce", accuser,
           f"{_name(game, accuser)} denunciou {_name(game, target)}: esqueceu o UNO! (+2 cartas)", target=target)


def _finish_round(game: dict, winner: str) -> None:
    points = sum(card_points(c) for pid, hand in game["hands"].items() if pid != winner for c in hand)
    game["scores"][winner] += points
    game["round_winner"] = winner
    game["round_points"] = points
    game["vulnerable"] = None
    game["pending"] = None
    if game["target"] <= 0 or game["scores"][winner] >= game["target"]:
        game["status"] = "game_over"
        game["winner"] = winner
        _event(game, "game_over", winner,
               f"{_name(game, winner)} venceu a partida! (+{points} pontos)", points=points)
    else:
        game["status"] = "round_over"
        _event(game, "round_over", winner,
               f"{_name(game, winner)} venceu a rodada {game['round']} e ganhou {points} pontos.", points=points)


def skip_player(game: dict, target: str) -> None:
    """Ação de anfitrião: pula a vez de um jogador ausente."""
    _require_playing(game)
    if whose_action(game) != target:
        raise GameError("Só dá para pular quem está na vez.")
    pending = game.get("pending")
    if pending and pending["type"] == "wild4":
        respond_wild4(game, target, False)
        return
    if pending and pending["type"] == "choose_color":
        choose_start_color(game, target, most_common_color(game["hands"][target]))
        pending = None
    game["pending"] = None
    _clear_vulnerable_if_other(game, target)
    _event(game, "skip_host", target, f"O anfitrião pulou a vez de {_name(game, target)} (ausente).", target=target)
    _advance(game, 1)


def most_common_color(hand: list[dict]) -> str:
    counts = Counter(c["color"] for c in hand if c["color"] in COLORS)
    if not counts:
        return COLORS[0]
    return counts.most_common(1)[0][0]


def hand_points(hand: list[dict]) -> int:
    return sum(card_points(c) for c in hand)


def total_cards(game: dict) -> int:
    return len(game["deck"]) + len(game["discard"]) + sum(len(h) for h in game["hands"].values())
