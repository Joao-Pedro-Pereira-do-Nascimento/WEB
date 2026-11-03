"""IA simples para os bots (e para jogar no lugar de quem caiu)."""

from __future__ import annotations

import random

from . import engine as E

BOT_NAMES = [
    "Bot Saci", "Bot Iara", "Bot Curupira", "Bot Boto", "Bot Cuca",
    "Bot Caipora", "Bot Boitatá", "Bot Matinta", "Bot Mapinguari",
]


def _choose_color(hand: list[dict], rng: random.Random) -> str:
    colored = [c for c in hand if c["color"] in E.COLORS]
    if not colored:
        return rng.choice(E.COLORS)
    return E.most_common_color(colored)


def _score_card(game: dict, pid: str, card: dict) -> float:
    """Heurística: quanto maior, melhor jogar essa carta agora."""
    nxt = E.next_player_id(game)
    danger = len(game["hands"][nxt]) <= 2
    hand = game["hands"][pid]
    same_color = sum(1 for c in hand if c["color"] == card["color"])
    if card["kind"] == "number":
        score = 10 + card["value"] + same_color * 2
    elif card["kind"] in ("skip", "reverse"):
        score = 22 + same_color * 2 + (30 if danger else 0)
    elif card["kind"] == "draw2":
        score = 24 + same_color * 2 + (40 if danger else 0)
    elif card["kind"] == "wild":
        score = 4 + (25 if len(hand) <= 2 else 0)
    else:  # wild4: guarda para o fim ou para emergências
        legal = not any(c["color"] == game["color"] for c in hand if c["id"] != card["id"])
        score = (2 if legal else -20) + (45 if danger else 0) + (25 if len(hand) <= 2 else 0)
    return score


def bot_step(game: dict, pid: str, rng: random.Random | None = None, careful: bool = False) -> str:
    """Executa uma decisão completa do bot ``pid``. Retorna uma descrição curta.
    ``careful`` (jogar automático de um humano): sempre grita UNO."""
    rng = rng or random.Random()
    if game["status"] != "playing":
        return "idle"
    if E.whose_action(game) != pid:
        return "idle"

    # Denunciar quem esqueceu o UNO (bots são atentos, mas não perfeitos).
    vul = game.get("vulnerable")
    if vul and vul != pid and rng.random() < 0.7:
        E.denounce(game, pid, vul, rng)

    pending = game.get("pending")
    if pending and pending["type"] == "choose_color":
        E.choose_start_color(game, pid, _choose_color(game["hands"][pid], rng))
        return "color"
    if pending and pending["type"] == "wild4":
        challenge = rng.random() < 0.3
        E.respond_wild4(game, pid, challenge, rng)
        return "challenge" if challenge else "accept"

    options = E.playable_cards(game, pid)
    if pending and pending["type"] == "drawn":
        if options:
            return _play(game, pid, options[0], rng, careful)
        E.pass_turn(game, pid)
        return "pass"
    if not options:
        E.draw_action(game, pid, rng)
        pending = game.get("pending")
        if pending and pending["type"] == "drawn":
            card = next(c for c in game["hands"][pid] if c["id"] == pending["card_id"])
            return _play(game, pid, card, rng, careful)
        return "draw"
    best = max(options, key=lambda c: (_score_card(game, pid, c), rng.random()))
    return _play(game, pid, best, rng, careful)


def _play(game: dict, pid: str, card: dict, rng: random.Random, careful: bool = False) -> str:
    if len(game["hands"][pid]) == 2 and E.can_shout_uno(game, pid) and (careful or rng.random() < 0.9):
        E.shout_uno(game, pid)
    color = None
    if card["kind"] in E.WILD_KINDS:
        rest = [c for c in game["hands"][pid] if c["id"] != card["id"]]
        color = _choose_color(rest, rng)
    E.play_card(game, pid, card["id"], color, rng)
    return "play"


def simulate_game(n_players: int, seed: int, target: int = 0, max_steps: int = 20000) -> dict:
    """Simula uma partida só com bots (usado nos testes)."""
    rng = random.Random(seed)
    pids = [f"b{i}" for i in range(n_players)]
    game = E.new_game(pids, {p: p for p in pids}, target=target, rng=rng)
    steps = 0
    while game["status"] != "game_over":
        if game["status"] == "round_over":
            E.next_round(game, rng)
        actor = E.whose_action(game)
        bot_step(game, actor, rng)
        steps += 1
        if steps > max_steps:
            raise RuntimeError("partida não terminou")
    game["_steps"] = steps
    return game
