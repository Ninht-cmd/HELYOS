"""Tests de LOGIQUE du reclassifieur par embeddings (embedder factice, sans Ollama).

Le vrai comportement (nomic-embed-text) est mesuré par eval/embedding_bench.py.
Ici on teste seulement la logique d'escalade/seuil avec un embedder déterministe.
"""

import unittest
import unicodedata

from jarvis_kernel.governance.embedding_reclassifier import EmbedderPort, EmbeddingReclassifier
from jarvis_kernel.governance.policy import Action, ActionType


def _norm(s):
    d = unicodedata.normalize("NFD", s.lower())
    return "".join(c for c in d if unicodedata.category(c) != "Mn")


class StubEmbedder(EmbedderPort):
    """Renvoie un one-hot 5D selon le mot-clé de nocivité (déterministe)."""

    def embed(self, text):
        t = _norm(text)
        if any(k in t for k in ("supprim", "effac", "ecras", "detrui", "/dev/null")):
            return [1, 0, 0, 0, 0]
        if any(k in t for k in ("virement", "paiement", "preleve", "transfer", "fonds")):
            return [0, 1, 0, 0, 0]
        if any(k in t for k in ("permission", "privileg", "droit", "autorisation")):
            return [0, 0, 1, 0, 0]
        if any(k in t for k in ("exterieur", "distant", "exfiltr", "dehors", "publier")):
            return [0, 0, 0, 1, 0]
        return [0, 0, 0, 0, 1]  # neutre


class TestEmbeddingReclassifierLogic(unittest.TestCase):
    def setUp(self):
        self.rc = EmbeddingReclassifier(StubEmbedder(), threshold=0.5)

    def test_escalates_when_semantically_harmful(self):
        self.assertEqual(
            self.rc.effective_type(Action(type=ActionType.WRITE_LOCAL, description="ecraser le fichier")),
            ActionType.DELETE)
        self.assertEqual(
            self.rc.effective_type(Action(type=ActionType.ANALYZE, description="faire un virement")),
            ActionType.FINANCIAL)

    def test_does_not_escalate_neutral_action(self):
        self.assertEqual(
            self.rc.effective_type(Action(type=ActionType.WRITE_LOCAL, description="rediger un document neutre")),
            ActionType.WRITE_LOCAL)

    def test_never_downgrades(self):
        # Une action deja DELETE reste DELETE (jamais vers moins nuisible).
        self.assertEqual(
            self.rc.effective_type(Action(type=ActionType.DELETE, description="texte neutre")),
            ActionType.DELETE)

    def test_threshold_gates_escalation(self):
        # Seuil a 1.1 : meme un match parfait (cos=1) ne passe pas -> pas d'escalade.
        strict = EmbeddingReclassifier(StubEmbedder(), threshold=1.1)
        self.assertEqual(
            strict.effective_type(Action(type=ActionType.WRITE_LOCAL, description="ecraser le fichier")),
            ActionType.WRITE_LOCAL)


if __name__ == "__main__":
    unittest.main()
