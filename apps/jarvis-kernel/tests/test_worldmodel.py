"""Tests du World Model : on prouve la MATH, pas juste que ça tourne.

Fusion bayésienne exacte, propagation d'incertitude, décroissance de confiance,
monotonie et pondération par confiance de l'utilité, classement des décisions.
"""

from __future__ import annotations

import math
import unittest

from jarvis_kernel.context import build_default_context
from jarvis_kernel.world.decision import Policy, utility
from jarvis_kernel.world.model import WorldModel
from jarvis_kernel.world.seed import default_actions, seed_world

NOW = 1_000_000.0
DAY = 86400.0


class TestBeliefUpdate(unittest.TestCase):
    def test_no_prior_adopts_measurement(self) -> None:
        w = WorldModel()
        b = w.observe("x", 100.0, 10.0, ts=NOW)
        self.assertAlmostEqual(b.value, 100.0)
        self.assertAlmostEqual(b.sigma, 10.0)

    def test_bayesian_fusion_equal_sigma(self) -> None:
        w = WorldModel()
        w.observe("x", 100.0, 10.0, ts=NOW)
        b = w.observe("x", 120.0, 10.0, ts=NOW)
        self.assertAlmostEqual(b.value, 110.0, places=6)              # moyenne
        self.assertAlmostEqual(b.sigma, math.sqrt(50.0), places=6)    # σ diminue: √50≈7.07

    def test_bayesian_fusion_pulls_toward_precise(self) -> None:
        w = WorldModel()
        w.observe("x", 100.0, 10.0, ts=NOW)          # peu sûr
        b = w.observe("x", 130.0, 5.0, ts=NOW)       # 4× plus précis
        self.assertAlmostEqual(b.value, 124.0, places=6)             # tiré vers 130
        self.assertAlmostEqual(b.sigma, math.sqrt(20.0), places=6)   # σ encore réduit


class TestUncertaintyAndConfidence(unittest.TestCase):
    def test_confidence_decays_with_age(self) -> None:
        w = WorldModel()
        b = w.set("cash", 1000.0, 5.0, ts=NOW, kind="money")
        fresh = b.confidence(NOW)
        old = b.confidence(NOW + 14 * DAY)          # une demi-vie plus tard
        self.assertGreater(fresh, old)
        self.assertAlmostEqual(old, fresh * 0.5, places=2)          # ~moitié

    def test_certainty_higher_when_sigma_lower(self) -> None:
        w = WorldModel()
        sure = w.set("a", 1000.0, 10.0, ts=NOW, kind="money")
        vague = w.set("b", 1000.0, 1000.0, ts=NOW, kind="money")
        self.assertGreater(sure.certainty(), vague.certainty())

    def test_uncertainty_propagation_runway(self) -> None:
        w = WorldModel()
        w.set("cash", 1000.0, 10.0, ts=NOW, kind="money")
        w.set("burn", 200.0, 50.0, ts=NOW, kind="money")
        r = w.derive("runway", lambda m: m["cash"] / m["burn"], ["cash", "burn"])
        self.assertAlmostEqual(r.value, 5.0, places=6)
        # σ analytique : √((1/200)²·10² + (1000/200²)²·50²) = √1.565 ≈ 1.251
        self.assertAlmostEqual(r.sigma, 1.2510, places=2)
        self.assertEqual(r.depends_on, ["cash", "burn"])


class TestUtility(unittest.TestCase):
    def _world(self, cash: float, risk: float) -> WorldModel:
        w = WorldModel()
        w.set("cash", cash, 1.0, ts=NOW, kind="money")
        w.set("risque_paiement", risk, 0.05, ts=NOW, kind="ratio")
        return w

    def test_more_cash_higher_utility(self) -> None:
        u_low, _ = utility(self._world(0.0, 0.0), NOW)
        u_high, _ = utility(self._world(50_000.0, 0.0), NOW)
        self.assertGreater(u_high, u_low)

    def test_more_risk_lower_utility(self) -> None:
        u_safe, _ = utility(self._world(1000.0, 0.0), NOW)
        u_risky, _ = utility(self._world(1000.0, 1.0), NOW)
        self.assertGreater(u_safe, u_risky)

    def test_low_confidence_pulls_less(self) -> None:
        # même valeur de cash, mais l'une fraîche, l'autre périmée -> contribue moins
        fresh = WorldModel(); fresh.set("cash", 50_000.0, 1.0, ts=NOW, kind="money")
        stale = WorldModel(); stale.set("cash", 50_000.0, 1.0, ts=NOW - 90 * DAY, kind="money")
        self.assertGreater(utility(fresh, NOW)[0], utility(stale, NOW)[0])

    def test_breakdown_is_inspectable(self) -> None:
        _, rows = utility(self._world(1000.0, 0.5), NOW)
        termes = {r["terme"] for r in rows}
        self.assertEqual(termes, {"cash", "revenu", "runway", "progres", "clients", "risque"})


class TestPolicy(unittest.TestCase):
    def test_decisions_ranked_and_risk_killers_win(self) -> None:
        ctx = build_default_context()
        w = seed_world(ctx, NOW)
        decisions = Policy().decide(w, default_actions(), NOW)
        self.assertEqual(len(decisions), 5)
        # classé par gain décroissant
        gains = [d.gain for d in decisions]
        self.assertEqual(gains, sorted(gains, reverse=True))
        # tuer un risque connu à 1.0 (Gumroad ou immatriculation) domine : c'est le vrai
        # ordre de priorité — le modèle le retrouve seul (cohérent avec le Pouls).
        self.assertIn(decisions[0].action.name, {"creer_gumroad", "immatriculation"})
        self.assertGreater(decisions[0].gain, 0.0)
        client = next(d for d in decisions if d.action.name == "premier_client")
        self.assertGreater(client.gain, 0.0)     # décrocher un client augmente aussi U


class TestSeedAndPersistence(unittest.TestCase):
    def test_seed_from_real_state(self) -> None:
        w = seed_world(build_default_context(), NOW)
        self.assertIsNotNone(w.get("cash"))
        self.assertEqual(w.get("risque_paiement").value, 1.0)     # aucun canal d'encaissement
        runway = w.get("runway_mois")
        self.assertEqual(runway.depends_on, ["cash", "burn_mensuel"])

    def test_persistence_roundtrip(self) -> None:
        w = WorldModel()
        w.set("cash", 1234.0, 7.0, ts=NOW, kind="money", source="test")
        w2 = WorldModel.from_dict(w.to_dict())
        b = w2.get("cash")
        self.assertAlmostEqual(b.value, 1234.0)
        self.assertAlmostEqual(b.sigma, 7.0)
        self.assertEqual(b.source, "test")


class TestWorldRouting(unittest.TestCase):
    def setUp(self) -> None:
        from jarvis_kernel.jarvis import Jarvis
        self.j = Jarvis(build_default_context())

    def test_routes_to_world(self) -> None:
        for msg in ("montre-moi l'état du monde", "quelle est ta décision ?",
                    "quelle action prioritaire maintenant ?", "ta fonction d'utilité ?"):
            self.assertEqual(self.j.classify(msg), "monde", msg)

    def test_handler_returns_decision(self) -> None:
        from jarvis_kernel.governance.autonomy import AutonomyLevel
        r = self.j._world("quelle est ta décision ?", AutonomyLevel.A1)
        self.assertEqual(r.intent, "monde")
        self.assertIn("U(S)", r.text)
        self.assertIn("ΔU", r.text)                 # une décision chiffrée, pas de la prose


if __name__ == "__main__":
    unittest.main()
