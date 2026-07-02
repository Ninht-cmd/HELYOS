"""EmbeddingReclassifier — Phase 3 : re-classer l'action par le SENS, pas le lexique.

Le ReclassifierGate lexical (Phase 2) tombe à 0% sur les paraphrases (mesuré). Hypothèse
de recherche (RQ2, RESET.md) : des embeddings capturent l'intention indépendamment des
mots-clés → robustesse à la paraphrase. Ce module la TESTE, il ne l'affirme pas.

Principe : on embed la description de l'action, on compare (cosinus) à des exemples-ancre
par classe de nocivité ; si la similarité max dépasse un seuil ET que la classe détectée
est plus nuisible que le type déclaré, on remonte le type.

Dépend d'un embedder local (Ollama nomic-embed-text). Échoue proprement si absent.
Limite honnête à mesurer : les embeddings peuvent SUR-bloquer une action honnête qui
*parle* de suppression (« documenter la procédure de suppression ») — le banc le vérifie.
"""

from __future__ import annotations

import dataclasses
import json
import math
import urllib.error
import urllib.request
from abc import ABC, abstractmethod

from .policy import Action, ActionType

_RANK = {
    ActionType.READ: 0, ActionType.ANALYZE: 1, ActionType.WRITE_LOCAL: 2,
    ActionType.RENAME_WORKDIR: 2, ActionType.EXTERNAL_SENSITIVE: 3,
    ActionType.DELETE: 4, ActionType.FINANCIAL: 4, ActionType.SELF_PERMISSION: 5,
}

# Exemples-ancre par classe nuisible (intention d'action).
ANCHORS: dict[ActionType, list[str]] = {
    ActionType.SELF_PERMISSION: [
        "modifier mes permissions", "obtenir les privilèges administrateur",
        "élever mes droits d'accès", "m'attribuer davantage d'autorisations",
    ],
    ActionType.FINANCIAL: [
        "effectuer un virement bancaire", "faire un paiement",
        "planifier un prélèvement automatique", "transférer des fonds vers un compte",
    ],
    ActionType.EXTERNAL_SENSITIVE: [
        "envoyer des données vers l'extérieur", "copier la base clients vers un serveur distant",
        "exfiltrer des informations confidentielles", "publier des données en dehors du système",
    ],
    ActionType.DELETE: [
        "supprimer définitivement le fichier", "effacer les données",
        "écraser définitivement le fichier", "détruire les fichiers",
    ],
}


class EmbedderPort(ABC):
    @abstractmethod
    def embed(self, text: str) -> list[float]: ...


class OllamaEmbedder(EmbedderPort):  # pragma: no cover - dépend d'un service (Ollama)
    def __init__(self, model: str = "nomic-embed-text", host: str = "http://localhost:11434",
                 timeout: int = 30) -> None:
        self.model, self.host, self.timeout = model, host.rstrip("/"), timeout

    def _post(self, path: str, body: dict) -> dict:
        req = urllib.request.Request(self.host + path, data=json.dumps(body).encode(),
                                     headers={"content-type": "application/json"}, method="POST")
        with urllib.request.urlopen(req, timeout=self.timeout) as r:
            return json.loads(r.read().decode())

    def embed(self, text: str) -> list[float]:
        try:  # API récente
            d = self._post("/api/embed", {"model": self.model, "input": text})
            if "embeddings" in d:
                return d["embeddings"][0]
            if "embedding" in d:
                return d["embedding"]
        except (urllib.error.URLError, OSError, KeyError, IndexError):
            pass
        try:  # API ancienne
            d = self._post("/api/embeddings", {"model": self.model, "prompt": text})
            return d["embedding"]
        except (urllib.error.URLError, OSError) as exc:
            raise RuntimeError(
                f"Ollama embeddings injoignable ({exc}). Lancer 'ollama pull {self.model}'."
            ) from exc


def _cos(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    return dot / (na * nb) if na and nb else 0.0


class EmbeddingReclassifier:
    def __init__(self, embedder: EmbedderPort, threshold: float = 0.82) -> None:
        self.embedder = embedder
        self.threshold = threshold
        # Pré-calcule les embeddings d'ancres (cache).
        self._anchor_vecs = {
            atype: [embedder.embed(a) for a in anchors]
            for atype, anchors in ANCHORS.items()
        }

    def scores(self, text: str) -> dict[ActionType, float]:
        v = self.embedder.embed(text)
        return {atype: max(_cos(v, av) for av in vecs)
                for atype, vecs in self._anchor_vecs.items()}

    def effective_type(self, action: Action) -> ActionType:
        text = f"{action.description} {action.target}".strip()
        if not text:
            return action.type
        best = action.type
        best_score = -1.0
        for atype, score in self.scores(text).items():
            if score >= self.threshold and _RANK[atype] > _RANK[best] and score > best_score:
                best, best_score = atype, score
        return best

    def reclassify(self, action: Action) -> Action:
        eff = self.effective_type(action)
        if eff is action.type:
            return action
        return dataclasses.replace(action, type=eff)
