"""Tests du Planner + Orchestrateur : objectif -> sous-objectifs -> agents -> plan gouverné."""

from __future__ import annotations

import unittest
from pathlib import Path

from jarvis_kernel.governance.autonomy import AutonomyLevel
from jarvis_kernel.governance.service import GovernanceService
from jarvis_kernel.world.domains.supply_chain_agent import read_receptions_csv
from jarvis_kernel.world.planner import Planner, default_orchestrator

CSV = Path(__file__).resolve().parents[3] / "data" / "receptions.csv"


class TestPlanner(unittest.TestCase):
    def test_cost_objective_decomposes_into_subgoals(self) -> None:
        subs = Planner().decompose("réduire les coûts de 15%")
        self.assertEqual(len(subs), 5)
        self.assertEqual(subs[-1].kind, "propose")
        self.assertTrue(subs[-1].side_effect)                       # l'étape finale a un effet externe
        self.assertEqual(subs[0].domain, "finance")
        self.assertIn("supply_chain", {s.domain for s in subs})

    def test_generic_objective_fallback(self) -> None:
        self.assertEqual(len(Planner().decompose("organise ma semaine")), 3)


class TestOrchestration(unittest.TestCase):
    def setUp(self) -> None:
        self.orch = default_orchestrator()
        self.ctx = {"rows": read_receptions_csv(CSV), "target": "FRN-07", "prior_lead_time": 9.0,
                    "annual_cost": 120000, "target_reduction_pct": 15}
        self.gov = GovernanceService()

    def test_routes_each_subgoal_to_right_agent(self) -> None:
        plan = self.orch.run("réduire les coûts de 15%", self.ctx,
                             governance=self.gov, granted=AutonomyLevel.A2)
        by_domain = {s["domaine"]: s["agent"] for s in plan["etapes"]}
        self.assertEqual(by_domain["finance"], "finance_agent")
        self.assertEqual(by_domain["supply_chain"], "supply_chain_agent")
        self.assertEqual(by_domain["general"], "general_advisor")

    def test_plan_is_explained_and_governed(self) -> None:
        plan = self.orch.run("réduire les coûts de 15%", self.ctx,
                             governance=self.gov, granted=AutonomyLevel.A5)
        self.assertEqual(len(plan["etapes"]), 5)
        # chaque étape est EXPLIQUÉE : résultat + confiance + sources
        for s in plan["etapes"]:
            self.assertIn("resultat", s)
            self.assertTrue(0 <= s["confiance"] <= 1)
            self.assertIsInstance(s["sources"], list)
        # finance calcule la vraie cible d'économie
        fin = next(s for s in plan["etapes"] if s["domaine"] == "finance")
        self.assertIn("18000", fin["resultat"].replace(" ", ""))   # 15% de 120000
        # supply chain s'appuie sur les vraies données
        sc = next(s for s in plan["etapes"] if s["domaine"] == "supply_chain")
        self.assertIn("data/receptions.csv", sc["sources"])
        # l'étape à effet externe est gouvernée -> validation requise, même à A5 (GR-2)
        self.assertTrue(plan["en_attente_validation"])
        prop = next(s for s in plan["etapes"] if s["kind"] == "propose")
        self.assertEqual(prop["gouvernance"]["decision"], "require_validation")


if __name__ == "__main__":
    unittest.main()
