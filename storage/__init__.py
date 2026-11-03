"""Escolha automática do armazenamento.

- ``st.secrets`` com a seção ``[firebase]`` **e** a chave ``database_url``
  -> Firebase Realtime Database (``RTDBBackend``) — o modo recomendado.
- ``[firebase]`` sem ``database_url`` -> Cloud Firestore (``FirebaseBackend``).
- Sem a seção ``[firebase]`` -> arquivos JSON locais em ``.data/`` (``LocalBackend``).
- Variável de ambiente ``UNO_BACKEND``: ``local`` força o modo local;
  ``firestore`` força o Firestore mesmo com ``database_url``.
  ``UNO_DATA_DIR`` muda a pasta dos dados locais.
"""

from __future__ import annotations

import os

from .base import Backend, NoChange, RoomNotFound
from .local import LocalBackend

__all__ = ["Backend", "NoChange", "RoomNotFound", "LocalBackend", "make_backend", "backend_label"]

LABELS = {"local": "arquivos locais", "firebase": "Firebase (Firestore)", "rtdb": "Firebase (Realtime Database)"}


def backend_label(be: Backend) -> str:
    return LABELS.get(getattr(be, "name", ""), str(getattr(be, "name", "?")))


def _firebase_secrets(secrets) -> dict | None:
    try:
        if secrets is not None and "firebase" in secrets:
            return dict(secrets["firebase"])
    except Exception:  # sem secrets.toml o Streamlit levanta erro ao acessar
        return None
    return None


def make_backend(secrets=None) -> tuple[Backend, str | None]:
    """Retorna (backend, aviso). O aviso explica um eventual fallback."""
    data_dir = os.environ.get("UNO_DATA_DIR", ".data")
    forced = os.environ.get("UNO_BACKEND", "").lower()
    if forced == "local":
        return LocalBackend(data_dir), None
    info = _firebase_secrets(secrets)
    if not info:
        return LocalBackend(data_dir), None
    url = str(info.pop("database_url", "") or info.pop("databaseURL", "") or "").strip()
    if url and forced != "firestore":
        try:
            from .rtdb import RTDBBackend

            return RTDBBackend(info, url), None
        except Exception as exc:  # credenciais erradas, pacote ausente...
            return LocalBackend(data_dir), f"Firebase Realtime Database indisponível ({exc}); usando armazenamento local."
    try:
        from .firebase import FirebaseBackend

        return FirebaseBackend(info), None
    except Exception as exc:
        return LocalBackend(data_dir), f"Firebase indisponível ({exc}); usando armazenamento local."
