"""Adaptateur PostgreSQL (optionnel) — même interface que SqliteMemoryStore.

Pour passer à l'échelle (état partagé, concurrence). Nécessite ``psycopg`` et un
Postgres en service (voir deploy/docker-compose.yml). Échoue clairement si absent,
plutôt que de dégrader silencieusement (le cœur reste sur SQLite/mémoire).
"""

from __future__ import annotations

import json
import time
from typing import Any

from .store import MemoryItem, MemoryStore


class PostgresMemoryStore(MemoryStore):  # pragma: no cover - dépend d'un service externe
    def __init__(self, dsn: str) -> None:
        try:
            import psycopg  # type: ignore
        except ImportError as exc:
            raise RuntimeError(
                "PostgresMemoryStore nécessite 'psycopg' (pip install 'psycopg[binary]')."
            ) from exc
        self._psycopg = psycopg
        self._dsn = dsn
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS memory (
                    namespace TEXT NOT NULL,
                    key       TEXT NOT NULL,
                    value     JSONB NOT NULL,
                    ts        DOUBLE PRECISION NOT NULL,
                    PRIMARY KEY (namespace, key)
                )
                """
            )

    def _connect(self):
        return self._psycopg.connect(self._dsn, autocommit=True)

    def remember(self, key: str, value: Any, namespace: str = "default") -> MemoryItem:
        ts = time.time()
        with self._connect() as conn:
            conn.execute(
                "INSERT INTO memory(namespace,key,value,ts) VALUES(%s,%s,%s,%s) "
                "ON CONFLICT (namespace,key) DO UPDATE SET value=EXCLUDED.value, ts=EXCLUDED.ts",
                (namespace, key, json.dumps(value, ensure_ascii=False), ts),
            )
        return MemoryItem(key=key, value=value, namespace=namespace, ts=ts)

    def recall(self, key: str, namespace: str = "default") -> Any | None:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT value FROM memory WHERE namespace=%s AND key=%s", (namespace, key)
            ).fetchone()
        return row[0] if row else None

    def forget(self, key: str, namespace: str = "default") -> bool:
        with self._connect() as conn:
            cur = conn.execute(
                "DELETE FROM memory WHERE namespace=%s AND key=%s", (namespace, key)
            )
        return cur.rowcount > 0

    def search(self, query: str, namespace: str = "default", limit: int = 10) -> list[MemoryItem]:
        like = f"%{query.lower()}%"
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT key,value,ts FROM memory WHERE namespace=%s "
                "AND (lower(key) LIKE %s OR lower(value::text) LIKE %s) "
                "ORDER BY ts DESC LIMIT %s",
                (namespace, like, like, limit),
            ).fetchall()
        return [MemoryItem(key=k, value=v, namespace=namespace, ts=ts) for (k, v, ts) in rows]

    def all(self, namespace: str = "default") -> list[MemoryItem]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT key,value,ts FROM memory WHERE namespace=%s ORDER BY ts", (namespace,)
            ).fetchall()
        return [MemoryItem(key=k, value=v, namespace=namespace, ts=ts) for (k, v, ts) in rows]
