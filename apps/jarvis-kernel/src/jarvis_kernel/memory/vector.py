"""Mémoire vectorielle — interface + repli local (stdlib) + adaptateur Qdrant.

Long terme / RAG (CODEX/07_TECH). Le repli ``NaiveVectorMemory`` fournit une
recherche sémantique approximative (sac-de-mots, cosinus) sans aucune dépendance,
pour rester Local First. ``QdrantVectorMemory`` (optionnel) branche un vrai moteur
vectoriel quand il est disponible. De vrais embeddings (Ollama, sentence-transformers)
remplaceront la vectorisation naïve derrière la même interface.
"""

from __future__ import annotations

import math
import re
from abc import ABC, abstractmethod
from collections import Counter
from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class VectorHit:
    id: str
    text: str
    score: float
    metadata: dict[str, Any] = field(default_factory=dict)


class VectorMemory(ABC):
    @abstractmethod
    def add(self, id: str, text: str, metadata: dict[str, Any] | None = None) -> None: ...

    @abstractmethod
    def search(self, query: str, limit: int = 5) -> list[VectorHit]: ...

    @abstractmethod
    def __len__(self) -> int: ...


_TOKEN = re.compile(r"[a-zà-ÿ0-9]+", re.IGNORECASE)


def _tokenize(text: str) -> Counter[str]:
    return Counter(_TOKEN.findall(text.lower()))


def _cosine(a: Counter[str], b: Counter[str]) -> float:
    if not a or not b:
        return 0.0
    common = set(a) & set(b)
    dot = sum(a[t] * b[t] for t in common)
    na = math.sqrt(sum(v * v for v in a.values()))
    nb = math.sqrt(sum(v * v for v in b.values()))
    return dot / (na * nb) if na and nb else 0.0


class NaiveVectorMemory(VectorMemory):
    """Repli local sans dépendance : similarité cosinus sac-de-mots.

    Suffisant pour une recherche sémantique approximative locale et déterministe ;
    remplaçable par Qdrant + embeddings réels sans changer les appelants.
    """

    def __init__(self) -> None:
        self._docs: dict[str, tuple[str, Counter[str], dict[str, Any]]] = {}

    def add(self, id: str, text: str, metadata: dict[str, Any] | None = None) -> None:
        self._docs[id] = (text, _tokenize(text), dict(metadata or {}))

    def search(self, query: str, limit: int = 5) -> list[VectorHit]:
        q = _tokenize(query)
        scored = [
            VectorHit(id=i, text=txt, score=_cosine(q, vec), metadata=meta)
            for i, (txt, vec, meta) in self._docs.items()
        ]
        scored = [h for h in scored if h.score > 0.0]
        scored.sort(key=lambda h: h.score, reverse=True)
        return scored[:limit]

    def __len__(self) -> int:
        return len(self._docs)


class QdrantVectorMemory(VectorMemory):  # pragma: no cover - dépend d'un service externe
    """Adaptateur Qdrant (optionnel). Nécessite ``qdrant-client`` et un embedder.

    Conservé volontairement minimal : à compléter (RFC) avec un vrai modèle
    d'embedding local (ex. via Ollama). Échoue clairement si les dépendances
    ou le service manquent, plutôt que de dégrader silencieusement.
    """

    def __init__(self, url: str = "http://localhost:6333", collection: str = "helyos") -> None:
        try:
            from qdrant_client import QdrantClient  # type: ignore
        except ImportError as exc:
            raise RuntimeError(
                "QdrantVectorMemory nécessite 'qdrant-client' "
                "(pip install qdrant-client) et un Qdrant en service."
            ) from exc
        self._client = QdrantClient(url=url)
        self._collection = collection
        # La création de collection / l'embedding sont à câbler par RFC.

    def add(self, id: str, text: str, metadata: dict[str, Any] | None = None) -> None:
        raise NotImplementedError("Embedding Qdrant à câbler par RFC (modèle local).")

    def search(self, query: str, limit: int = 5) -> list[VectorHit]:
        raise NotImplementedError("Embedding Qdrant à câbler par RFC (modèle local).")

    def __len__(self) -> int:
        return 0
