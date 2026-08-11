"""Cockpit ENTREPRISE (Front B) : la vue du dirigeant, alimentée par des données RÉELLES.

Garde-fou anti-« coquille vide » : aucun chiffre n'est inventé. L'argent vient du livre de
caisse (0 tant qu'aucune écriture), le pipeline de la prospection, les opérations du Pouls /
de la gouvernance / du portefeuille. On vérifie la structure ET l'honnêteté (0 → « à connecter »,
jamais un CA fabriqué)."""

from __future__ import annotations

import unittest

from fastapi.testclient import TestClient

from jarvis_kernel.main import create_app


class TestOsCockpit(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.client = TestClient(create_app())

    def test_root_is_the_enterprise_cockpit(self) -> None:
        r = self.client.get("/", follow_redirects=False)
        self.assertIn(r.status_code, (302, 307))
        self.assertEqual(r.headers["location"], "/app/os.html")

    def test_payload_is_real_and_structured(self) -> None:
        d = self.client.get("/os/cockpit").json()
        # score transparent, borné, avec ses parts
        self.assertIsInstance(d["score"]["value"], int)
        self.assertTrue(0 <= d["score"]["value"] <= 100)
        self.assertIn("gouvernance", d["score"]["parts"])
        # opérations réelles : le compteur affiché = le nombre d'items
        self.assertEqual(d["operations"]["count"], len(d["operations"]["items"]))
        self.assertGreaterEqual(d["operations"]["count"], 1)
        # le département Engineering (le vrai travail déjà construit) est ACTIF
        eng = next(x for x in d["departments"] if x["key"] == "engineering")
        self.assertEqual(eng["status"], "actif")
        self.assertIsInstance(d["waiting_on_you"], list)
        # AI-first : HELYOS opère, le manuel reste disponible
        self.assertEqual(d["operator"]["mode"], "ai-first")
        self.assertTrue(d["operator"]["manual_available"])

    def test_money_is_honest_not_fabricated(self) -> None:
        d = self.client.get("/os/cockpit").json()
        ca = next(k for k in d["kpis"] if k["key"] == "ca")
        # sans écriture de caisse, le CA est 0 et clairement « à connecter » (pas un faux 142 580 €)
        self.assertEqual(ca["value"], 0)
        self.assertEqual(ca["state"], "à connecter")
        self.assertEqual(ca["source"], "ledger")


if __name__ == "__main__":
    unittest.main()
