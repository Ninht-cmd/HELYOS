"""Tests de la boucle outcome->plan : R = observé/attendu, catégories, et LE critère
comportemental (réutiliser le gain, ne pas répéter la décision, chercher d'autres leviers)."""

from __future__ import annotations

import unittest
from pathlib import Path

from jarvis_kernel.governance.autonomy import AutonomyLevel
from jarvis_kernel.governance.service import GovernanceService
from jarvis_kernel.world.memory_store import UnifiedMemory
from jarvis_kernel.world.outcome import OutcomeAnalyzer, classify
from jarvis_kernel.world.domains.supply_chain_agent import read_receptions_csv
from jarvis_kernel.world.planner import default_orchestrator

CSV = Path(__file__).resolve().parents[3] / "data" / "receptions.csv"
PARAMS = dict(demand=10, sigma_demand=2, sigma_lead_time=1, service_level=0.95,
              annual_demand=3650, order_cost=50, holding_cost=2, stockout_cost=20)


class TestRatioClassification(unittest.TestCase):
    def test_categories(self) -> None:
        self.assertEqual(classify(1.0), "success")
        self.assertEqual(classify(15 / 15), "success")
        self.assertEqual(classify(11.8 / 15), "partial_success")     # 0.787
        self.assertEqual(classify(0.3), "weak_success")
        self.assertEqual(classify(-0.1), "failure")
        self.assertEqual(classify(None), "indetermine")

    def test_thresholds_configurable(self) -> None:
        strict = {"success": 0.99, "partial": 0.90, "weak": 0.0}     # domaine exigeant
        self.assertEqual(classify(0.95, strict), "partial_success")  # 0.95 n'est plus 'success'
        self.assertEqual(classify(0.85, strict), "weak_success")     # sous le seuil partial resserré
        self.assertEqual(classify(0.95), "success")                  # 'success' avec les seuils par défaut


class TestOutcomeLoopChangesPlan(unittest.TestCase):
    """RUN #1 outcome confirmé (partiel) -> RUN #2 réutilise le gain, cherche ailleurs."""

    def setUp(self) -> None:
        self.mem = UnifiedMemory()
        self.orch = default_orchestrator()
        self.gov = GovernanceService()
        self.ctx = {"rows": read_receptions_csv(CSV), "target": "FRN-07",
                    "prior_lead_time": 9.0, "policy_params": PARAMS}

    def test_behavioural_acceptance(self) -> None:
        # RUN #1 : l'agent choisit FRN-12 (étape compare) -> validation -> outcome mesuré
        r1 = self.orch.run("Réduire les coûts de 15%", self.ctx, governance=self.gov,
                           granted=AutonomyLevel.A2, memory=self.mem)
        comp = next(s for s in r1["etapes"] if s["kind"] == "compare")
        did = comp["decision_id"]
        self.assertIsNotNone(did)
        self.assertIn("Passage vers FRN-12", self.mem.decisions[did].content)
        self.mem.set_decision_status(did, "validated", "je valide FRN-12")
        self.mem.record_outcome(did, observed=11.8, expected=15.0, note="économie partielle")
        self.mem.set_decision_status(did, "confirmed")

        # RUN #2 : « Continue à réduire mes coûts » — le plan doit CHANGER
        r2 = self.orch.run("Continue à réduire mes coûts", self.ctx, governance=self.gov,
                           granted=AutonomyLevel.A2, memory=self.mem)
        self.assertIn("3.2", r2["memory_context"])                   # écart restant retrouvé
        self.assertIn("78.7", r2["memory_context"])                  # ratio calculé
        self.assertTrue(r2["reuses_confirmed_gain"])                 # conserve le gain
        self.assertNotIn("Passage vers FRN-12", r2["decisions_proposees"])  # ne répète PAS
        self.assertGreaterEqual(r2["nouveaux_leviers"], 2)           # cherche d'autres leviers

    def test_agent_scorecard_metacognition(self) -> None:
        r1 = self.orch.run("Réduire les coûts de 15%", self.ctx, governance=self.gov,
                           granted=AutonomyLevel.A2, memory=self.mem)
        did = next(s for s in r1["etapes"] if s["kind"] == "compare")["decision_id"]
        self.mem.record_outcome(did, observed=11.8, expected=15.0)
        card = OutcomeAnalyzer().agent_scorecard(self.mem)
        self.assertIn("supply_chain_agent", card)
        self.assertEqual(card["supply_chain_agent"]["confirmes"], 1)     # 1 décision confirmée
        self.assertEqual(card["supply_chain_agent"]["confiance_calibree"], 1.0)


if __name__ == "__main__":
    unittest.main()
