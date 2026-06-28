"""Mémoire persistante sur SQLite — Local First, zéro service externe.

C'est l'implémentation persistante par défaut : la mémoire survit au redémarrage
sans exiger Postgres ni Docker (ADN 2). L'adaptateur Postgres
(``postgres_store.py``) suit la même interface pour passer à l'échelle.
"""

from __future__ import annotations

import json
import os
import sqlite3
import time
from pathlib import Path
from typing import Any

from .store import MemoryItem, MemoryStore


class SqliteMemoryStore(MemoryStore):
    """Stockage clé/valeur persistant par namespace, en SQLite (stdlib)."""

    def __init__(self, path: str | os.PathLike[str] = "helyos_memory.sqlite") -> None:
        self.path = Path(path)
        if self.path.parent and str(self.path.parent) not in ("", "."):
            self.path.parent.mkdir(parents=True, exist_ok=True)
        # check_same_thread=False : l'API peut servir depuis plusieurs threads.
        self._conn = sqlite3.connect(str(self.path), check_same_thread=False)
        self._conn.execute(
            """
            CREATE TABLE IF NOT EXISTS memory (
                namespace TEXT NOT NULL,
                key       TEXT NOT NULL,
                value     TEXT NOT NULL,
                ts        REAL NOT NULL,
                PRIMARY KEY (namespace, key)
            )
            """
        )
        self._conn.commit()

    def remember(self, key: str, value: Any, namespace: str = "default") -> MemoryItem:
        ts = time.time()
        self._conn.execute(
            "INSERT INTO memory(namespace, key, value, ts) VALUES(?,?,?,?) "
            "ON CONFLICT(namespace, key) DO UPDATE SET value=excluded.value, ts=excluded.ts",
            (namespace, key, json.dumps(value, ensure_ascii=False), ts),
        )
        self._conn.commit()
        return MemoryItem(key=key, value=value, namespace=namespace, ts=ts)

    def recall(self, key: str, namespace: str = "default") -> Any | None:
        row = self._conn.execute(
            "SELECT value FROM memory WHERE namespace=? AND key=?", (namespace, key)
        ).fetchone()
        return json.loads(row[0]) if row is not None else None

    def forget(self, key: str, namespace: str = "default") -> bool:
        cur = self._conn.execute(
            "DELETE FROM memory WHERE namespace=? AND key=?", (namespace, key)
        )
        self._conn.commit()
        return cur.rowcount > 0

    def search(self, query: str, namespace: str = "default", limit: int = 10) -> list[MemoryItem]:
        like = f"%{query.lower()}%"
        rows = self._conn.execute(
            "SELECT key, value, ts FROM memory WHERE namespace=? "
            "AND (lower(key) LIKE ? OR lower(value) LIKE ?) ORDER BY ts DESC LIMIT ?",
            (namespace, like, like, limit),
        ).fetchall()
        return [
            MemoryItem(key=k, value=json.loads(v), namespace=namespace, ts=ts)
            for (k, v, ts) in rows
        ]

    def all(self, namespace: str = "default") -> list[MemoryItem]:
        rows = self._conn.execute(
            "SELECT key, value, ts FROM memory WHERE namespace=? ORDER BY ts", (namespace,)
        ).fetchall()
        return [
            MemoryItem(key=k, value=json.loads(v), namespace=namespace, ts=ts)
            for (k, v, ts) in rows
        ]

    def close(self) -> None:
        self._conn.close()
