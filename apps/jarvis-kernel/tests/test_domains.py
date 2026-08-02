"""Tests du Domain Layer v2.0 : équations réelles + injection ontologique + MC usine."""

from __future__ import annotations

import math
import unittest

from jarvis_kernel.world.domains import build_ontology, full_ontology
from jarvis_kernel.world.domains.engineering import (ENGINEERING, oee, safety_factor,
                                                     unit_cost, wire_machine, wire_part_safety)
from jarvis_kernel.world.domains.finance import (FINANCE, irr, npv, payback_period,
                                                 roi, wire_finance)
from jarvis_kernel.world.ontology import KnowledgeGraph
from jarvis_kernel.world.simulation import StochasticEvent, Plan, monte_carlo_metric

NOW = 1_000_000.0


class TestFinanceEquations(unittest.TestCase):
    def test_npv_exact(self) -> None:
        # -1000 aujourd'hui, +1100 dans 1 an à 10% -> VAN = 0
        self.assertAlmostEqual(npv(0.10, [-1000, 1100]), 0.0, places=6)

    def test_irr_solves_npv_zero(self) -> None:
        cf = [-1000, 300, 300, 300, 300, 300]
        r = irr(cf)
        self.assertIsNotNone(r)
        self.assertAlmostEqual(npv(r, cf), 0.0, places=4)     # TRI annule bien la VAN
        self.assertTrue(0.10 < r < 0.20)                       # ~15.2%

    def test_roi_and_payback(self) -> None:
        self.assertAlmostEqual(roi(1500, 1000), 0.5)
        self.assertEqual(payback_period([-1000, 400, 400, 400]), 3)


class TestEngineeringEquations(unittest.TestCase):
    def test_oee(self) -> None:
        self.assertAlmostEqual(oee(0.9, 0.95, 0.98), 0.9 * 0.95 * 0.98)

    def test_safety_factor(self) -> None:
        self.assertAlmostEqual(safety_factor(250.0, 100.0), 2.5)   # limite/contrainte

    def test_unit_cost(self) -> None:
        # matière 1200 + assemblage 450 + 6h × 25€/h = 1800
        self.assertAlmostEqual(unit_cost(1200, 450, 25, 6), 1800.0)


class TestOntologyInjection(unittest.TestCase):
    def test_domains_inject_and_enrich_types(self) -> None:
        o = build_ontology(FINANCE, ENGINEERING)
        self.assertIn("BusinessUnit", o.entity_types)               # type injecté par Finance
        # Engineering ENRICHIT Machine sans écraser ses attributs d'origine
        machine = o.entity_type("Machine").attrs
        self.assertIn("oee", machine)                               # attribut de domaine ajouté
        self.assertIn("capacite", machine)                         # attribut d'origine conservé
        self.assertIn("coef_securite", o.entity_type("Part").attrs)


class TestRobotFactorySimulation(unittest.TestCase):
    """L'exemple du fondateur : usine de robots, distribution de profit sur N futurs."""

    def _factory(self) -> KnowledgeGraph:
        g = KnowledgeGraph(full_ontology())
        g.add_entity("BusinessUnit", "robot_bu", "Unité robotique", now=NOW,
                     values={"capex": 150_000, "opex": 20_000, "revenus": 65_000, "couts": 40_000,
                             "cash": 200_000})
        g.add_entity("Machine", "cnc", "Centre CNC", now=NOW,
                     values={"disponibilite": 0.94, "performance": 0.9, "qualite": 0.98,
                             "capacite": 800})
        g.add_entity("Part", "chassis", "Châssis alu", now=NOW,
                     values={"limite_elastique": 250.0, "contrainte_max": 90.0})
        wire_finance(g, "robot_bu")
        wire_machine(g, "cnc")
        wire_part_safety(g, "chassis")
        return g

    def test_wired_derivations(self) -> None:
        g = self._factory()
        self.assertAlmostEqual(g.value("cnc", "oee"), 0.94 * 0.9 * 0.98, places=6)
        self.assertAlmostEqual(g.value("chassis", "coef_securite"), 250.0 / 90.0, places=4)
        self.assertAlmostEqual(g.value("robot_bu", "marge_brute"), (65_000 - 40_000) / 65_000, places=6)

    def test_monte_carlo_profit_distribution(self) -> None:
        g = self._factory()
        profit = lambda gr: (gr.value("robot_bu", "revenus") - gr.value("robot_bu", "couts")) * 12
        # événement : l'acier +30% pousse les coûts, menace le profit
        acier = Plan("choc acier possible",
                     events=[StochasticEvent("acier +30%", 0.35, {"robot_bu.couts": 1.3}, op="mul")])
        d = monte_carlo_metric(g, profit, NOW, plan=acier, n=3000, seed=11)
        for k in ("mean", "std", "p5", "p50", "p95", "p_negatif"):
            self.assertIn(k, d)
        self.assertLess(d["p5"], d["p50"])
        self.assertLess(d["p50"], d["p95"])
        self.assertGreaterEqual(d["p_negatif"], 0.0)               # une part des futurs peut être déficitaire


if __name__ == "__main__":
    unittest.main()
