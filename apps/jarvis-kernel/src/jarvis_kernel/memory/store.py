"""Interface de mémoire et implémentation en mémoire (Local First).

L'implémentation par défaut ne dépend d'aucun service externe. Une implémentation
Postgres/Qdrant pourra la remplacer derrière la même interface abstraite.
"""

from __future__ import annotations

import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class MemoryItem:
    key: str
    value: Any
    namespace: str = "default"
    ts: float = field(default_factory=time.time)


class MemoryStore(ABC):
    """Contrat de mémoire. Court terme et long terme partagent cette interface."""

    @abstractmethod
    def remember(self, key: str, value: Any, namespace: str = "default") -> MemoryItem:
        ...

    @abstractmethod
    def recall(self, key: str, namespace: str = "default") -> Any | None:
        ...

    @abstractmethod
    def forget(self, key: str, namespace: str = "default") -> bool:
        ...

    @abstractmethod
    def search(self, query: str, namespace: str = "default", limit: int = 10) -> list[MemoryItem]:
        """Recherche naïve (sous-chaîne) en v0 ; cible : vectorielle (Qdrant)."""
        ...

    @abstractmethod
    def all(self, namespace: str = "default") -> list[MemoryItem]:
        ...


class InMemoryMemoryStore(MemoryStore):
    """Implémentation en mémoire, sans dépendance."""

    def __init__(self) -> None:
        # namespace -> key -> MemoryItem
        self._data: dict[str, dict[str, MemoryItem]] = {}

    def remember(self, key: str, value: Any, namespace: str = "default") -> MemoryItem:
        item = MemoryItem(key=key, value=value, namespace=namespace)
        self._data.setdefault(namespace, {})[key] = item
        return item

    def recall(self, key: str, namespace: str = "default") -> Any | None:
        item = self._data.get(namespace, {}).get(key)
        return item.value if item is not None else None

    def forget(self, key: str, namespace: str = "default") -> bool:
        ns = self._data.get(namespace, {})
        if key in ns:
            del ns[key]
            return True
        return False

    def search(self, query: str, namespace: str = "default", limit: int = 10) -> list[MemoryItem]:
        q = query.lower()
        results = [
            item
            for item in self._data.get(namespace, {}).values()
            if q in str(item.key).lower() or q in str(item.value).lower()
        ]
        return results[:limit]

    def all(self, namespace: str = "default") -> list[MemoryItem]:
        return list(self._data.get(namespace, {}).values())
