"""Interface comum dos armazenamentos (arquivo local, Firestore ou Realtime Database)."""

from __future__ import annotations

from typing import Any, Callable


class RoomNotFound(Exception):
    pass


class NoChange(Exception):
    """Levante dentro de ``fn`` para abortar a transação sem gravar nada
    (ex.: o bot já jogou por outro cliente). A exceção chega a quem chamou."""


class Backend:
    """Contrato mínimo usado pelo app.

    - ``transact(code, fn)``: lê a sala, executa ``fn(state)`` (que altera o
      estado ou levanta exceção), incrementa ``version`` e grava — tudo de forma
      atômica (trava de arquivo ou transação do Firestore). Retorna
      ``(state, resultado_de_fn)``.
    """

    name = "base"
    poll_seconds = 1.5

    def create_room(self, code: str, state: dict) -> bool:  # False se já existir
        raise NotImplementedError

    def get_room(self, code: str) -> dict | None:
        raise NotImplementedError

    def transact(self, code: str, fn: Callable[[dict], Any]) -> tuple[dict, Any]:
        raise NotImplementedError

    def heartbeat(self, code: str, pid: str, ts: float) -> None:
        raise NotImplementedError

    def presence(self, code: str) -> dict[str, float]:
        raise NotImplementedError

    def record_stats(self, entries: list[tuple[str, str, dict]], game_id: str | None = None) -> None:
        """Soma as estatísticas. Com ``game_id``, a mesma partida nunca é contada duas vezes."""
        raise NotImplementedError

    def ranking(self) -> list[dict]:
        raise NotImplementedError

    # documentos genéricos (contas, sessões, limite de tentativas): ``coll`` é um nome
    # fixo ("users", "sessions", "limits"); ``key`` já vem normalizada pelo chamador.
    def doc_get(self, coll: str, key: str) -> dict | None:
        raise NotImplementedError

    def doc_update(self, coll: str, key: str, fn: Callable[[dict | None], tuple[dict | None, Any]]) -> Any:
        """Lê o documento, roda ``fn(atual)`` -> ``(novo, resultado)`` e grava ``novo``
        de forma atômica (``None`` apaga). Exceção em ``fn`` => nada é gravado.
        Retorna ``resultado``."""
        raise NotImplementedError


STAT_FIELDS = [
    "games", "wins", "points", "cards_played", "cards_drawn", "uno_shouts",
    "denounces", "penalties", "wild4_played", "action_played",
]
