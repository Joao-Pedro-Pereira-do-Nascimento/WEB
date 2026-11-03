"""Personagens do folclore que o jogador escolhe como avatar (dados puros, sem desenho).

O desenho de cada medalhão fica em ``ui/icons.py``. Salas antigas guardavam
chaves de elementos (``fogo``, ``folha``...): ``normalize`` converte para um
personagem, então elas continuam aparecendo com um retrato.
"""

from __future__ import annotations

import random

# chave -> (nome curto para a legenda, nome completo)
CHARACTERS: dict[str, tuple[str, str]] = {
    "saci": ("Saci", "Saci-Pererê"),
    "curupira": ("Curupira", "Curupira"),
    "iara": ("Iara", "Iara"),
    "cuca": ("Cuca", "Cuca"),
    "mula": ("Mula", "Mula sem Cabeça"),
    "boitata": ("Boitatá", "Boitatá"),
    "boto": ("Boto", "Boto-cor-de-rosa"),
    "caipora": ("Caipora", "Caipora"),
    "negrinho": ("Negrinho", "Negrinho do Pastoreio"),
    "lobisomem": ("Lobisomem", "Lobisomem"),
    "mapinguari": ("Mapinguari", "Mapinguari"),
    "boi_bumba": ("Boi-bumbá", "Boi-bumbá"),
    "matinta": ("Matinta", "Matinta Pereira"),
    "boiuna": ("Boiúna", "Cobra-Grande (Boiúna)"),
}
KEYS: list[str] = list(CHARACTERS)

# chaves antigas (elementos) -> personagem
LEGACY: dict[str, str] = {
    "fogo": "boitata", "folha": "curupira", "onda": "iara", "sol": "saci", "boto": "boto",
    "cobra": "boiuna", "lua": "lobisomem", "coruja": "matinta", "javali": "caipora",
    "boi": "boi_bumba", "flor": "cuca", "vela": "negrinho",
}


def normalize(key: str | None) -> str | None:
    """Chave atual do personagem (aceita chaves antigas); ``None`` se desconhecida."""
    if key in CHARACTERS:
        return key
    return LEGACY.get(key or "")


def short_name(key: str | None) -> str:
    k = normalize(key)
    return CHARACTERS[k][0] if k else "?"


def full_name(key: str | None) -> str:
    k = normalize(key)
    return CHARACTERS[k][1] if k else "?"


def used_in(players: list[dict], exclude_pid: str | None = None) -> set[str]:
    """Personagens já escolhidos (normalizados) pelos jogadores, menos ``exclude_pid``."""
    return {k for p in players if p.get("id") != exclude_pid
            for k in [normalize(p.get("avatar"))] if k}


def free(players: list[dict], exclude_pid: str | None = None) -> list[str]:
    used = used_in(players, exclude_pid)
    return [k for k in KEYS if k not in used]


def pick_free(players: list[dict], prefer: str | None = None, rng: random.Random | None = None) -> str:
    """``prefer`` se estiver livre; senão um personagem livre sorteado (ou qualquer um, se acabarem)."""
    options = free(players)
    prefer = normalize(prefer)
    if prefer in options:
        return prefer
    return (rng or random).choice(options or KEYS)
