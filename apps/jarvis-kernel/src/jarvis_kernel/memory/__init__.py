"""Mémoire de Jarvis — interface + backends (mémoire, SQLite, Postgres) + vectoriel.

Sélection du backend via ``build_memory()`` (piloté par la config). L'interface
``MemoryStore`` isole l'implémentation (modularité, ADN 4) — CODEX/07_TECH.
"""

from __future__ import annotations

from .sqlite_store import SqliteMemoryStore
from .store import InMemoryMemoryStore, MemoryItem, MemoryStore
from .vector import NaiveVectorMemory, VectorHit, VectorMemory

__all__ = [
    "MemoryStore",
    "InMemoryMemoryStore",
    "SqliteMemoryStore",
    "MemoryItem",
    "VectorMemory",
    "NaiveVectorMemory",
    "VectorHit",
    "build_memory",
]


def build_memory(backend: str = "memory", **kwargs) -> MemoryStore:
    """Fabrique un MemoryStore selon le backend demandé.

    - ``memory``   : volatile (tests, défaut le plus simple).
    - ``sqlite``   : persistant local, zéro service (recommandé hors tests).
    - ``postgres`` : à l'échelle (nécessite psycopg + un Postgres ; DSN requis).
    """
    backend = (backend or "memory").lower()
    if backend == "memory":
        return InMemoryMemoryStore()
    if backend == "sqlite":
        return SqliteMemoryStore(kwargs.get("path", "helyos_memory.sqlite"))
    if backend == "postgres":
        from .postgres_store import PostgresMemoryStore

        dsn = kwargs.get("dsn")
        if not dsn:
            raise ValueError("backend postgres : 'dsn' requis (ex. postgresql://...).")
        return PostgresMemoryStore(dsn)
    raise ValueError(f"Backend mémoire inconnu : {backend!r} (memory|sqlite|postgres).")
