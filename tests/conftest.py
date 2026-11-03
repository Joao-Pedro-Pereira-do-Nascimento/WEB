import os
import random
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from game import engine as E  # noqa: E402


def card(color, kind="number", value=None, cid=None):
    if kind == "number" and value is None:
        value = 0
    cid = cid or f"t-{color}-{kind}-{value}-{random.random():.8f}"
    return {"id": cid, "color": color, "kind": kind, "value": value if kind == "number" else None}


def setup_game(hands: dict, top: dict, color: str | None = None, current: int = 0,
               direction: int = 1, deck: list | None = None, seed: int = 1) -> dict:
    """Partida com mãos/descarte controlados para testar regras específicas."""
    pids = list(hands)
    game = E.new_game(pids, {p: p.upper() for p in pids}, rng=random.Random(seed))
    game["hands"] = {p: list(h) for p, h in hands.items()}
    game["discard"] = [top]
    game["color"] = color or top["color"]
    game["current"] = current
    game["direction"] = direction
    game["pending"] = None
    game["vulnerable"] = None
    game["uno_safe"] = []
    if deck is not None:
        game["deck"] = list(deck)
    return game


@pytest.fixture
def rng():
    return random.Random(42)


@pytest.fixture
def data_dir(tmp_path, monkeypatch):
    d = tmp_path / "data"
    monkeypatch.setenv("UNO_DATA_DIR", str(d))
    monkeypatch.setenv("UNO_BACKEND", "local")
    return d
