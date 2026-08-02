"""Tests du Simulation Engine v1.3 : Monte-Carlo, événements stochastiques, Risk
Engine, Trajectory Ranking (+ garde-fou ressources v1.2), apprentissage causal."""

from __future__ import annotations

import unittest

from jarvis_kernel.world.ontology import KnowledgeGraph, default_ontology
from jarvis_kernel.world.reality import Response
from jarvis_kernel.world.simulation import (Plan, StochasticEvent, feasible_resources,
                                            learn_elasticity, monte_carlo,
                                            rank_trajectories, risk_adjusted)

NOW = 1_000_000.0


def _co() -> KnowledgeGraph:
    g = KnowledgeGraph(default_ontology())
    g.add_entity("Company", "co", "Boîte", now=NOW,
                 values={"marge": 0.5, "croissance": 0.1, "risque": 0.2, "runway_mois": 6})
    g.set_attr("co", "cash", 10_000.0, sigma=300.0, now=NOW)     # peu de bruit sur le cash
    return g


# Plans « projet risqué » vs « projet sûr » (l'exemple du fondateur : gros gain/risque élevé
# contre gain modéré/risque faible). La faillite met le cash à -1000 (compté comme ruine).
def _plan_A() -> Plan:
    return Plan("A · gros pari", actions=[Response("gain", [("co.cash", "add", 80_000)])],
                events=[StochasticEvent("faillite A", 0.40, {"co.cash": -1000.0}, op="set")])


def _plan_B() -> Plan:
    return Plan("B · prudent", actions=[Response("gain", [("co.cash", "add", 25_000)])],
                events=[StochasticEvent("faillite B", 0.05, {"co.cash": -1000.0}, op="set")])


class TestMonteCarlo(unittest.TestCase):
    def test_distribution_shape_and_determinism(self) -> None:
        d1 = monte_carlo(_co(), "co", _plan_B(), NOW, n=1500, seed=7)
        d2 = monte_carlo(_co(), "co", _plan_B(), NOW, n=1500, seed=7)
        self.assertEqual(d1, d2)                                   # même graine -> même distribution
        for k in ("mean", "std", "p5", "p50", "p95", "cvar5", "p_faillite"):
            self.assertIn(k, d1)
        self.assertLessEqual(d1["p5"], d1["p50"])
        self.assertLessEqual(d1["p50"], d1["p95"])

    def test_stochastic_event_drives_failure_rate(self) -> None:
        dA = monte_carlo(_co(), "co", _plan_A(), NOW, n=4000, seed=1)
        dB = monte_carlo(_co(), "co", _plan_B(), NOW, n=4000, seed=1)
        self.assertAlmostEqual(dA["p_faillite"], 0.40, delta=0.04)  # l'événement à 40% se voit
        self.assertAlmostEqual(dB["p_faillite"], 0.05, delta=0.03)
        self.assertGreater(dA["std"], dB["std"])                    # A est plus risqué


class TestRiskEngine(unittest.TestCase):
    def test_choice_depends_on_risk_aversion(self) -> None:
        g = _co()
        plans = [_plan_A(), _plan_B()]
        # joueur (λ faible) : le gros pari domine par l'espérance
        greedy = rank_trajectories(g, "co", plans, NOW, risk_aversion=0.2, n=4000, seed=3)
        # prudent (λ élevé) : la variance de A est pénalisée -> le plan sûr gagne
        careful = rank_trajectories(g, "co", plans, NOW, risk_aversion=3.0, n=4000, seed=3)
        self.assertEqual(greedy[0]["plan"], "A · gros pari")
        self.assertEqual(careful[0]["plan"], "B · prudent")        # LA MÊME question, choix inversé


class TestResourceGuard(unittest.TestCase):
    def test_granular_feasibility(self) -> None:
        g = _co()
        g.add_entity("Resource", "ing_ia", "Ingénieur IA", now=NOW,
                     values={"quantite": 1, "disponibilite": 1.0}, meta={"kind": "human"})
        g.add_entity("Resource", "commercial", "Commercial", now=NOW,
                     values={"quantite": 1, "disponibilite": 1.0}, meta={"kind": "human"})
        # par ressource PRÉCISE : 2 ingénieurs IA demandés, 1 dispo -> infaisable
        ok, lacks = feasible_resources(g, {"ing_ia": 2})
        self.assertFalse(ok)
        self.assertEqual(lacks, {"ing_ia": 1.0})
        # par nature : 2 humains dispo au total
        self.assertTrue(feasible_resources(g, {"human": 2})[0])

    def test_infeasible_plan_is_dropped_from_ranking(self) -> None:
        g = _co()
        impossible = Plan("Projet impossible", actions=[Response("x", [("co.cash", "add", 1)])],
                          needs={"ing_ia": 3})
        ranked = rank_trajectories(g, "co", [_plan_B(), impossible], NOW, n=800, seed=2)
        self.assertFalse(ranked[-1]["faisable"])                   # l'impossible finit dernier
        self.assertEqual(ranked[-1]["plan"], "Projet impossible")


class TestCausalLearning(unittest.TestCase):
    def test_recovers_known_coefficient(self) -> None:
        pairs = [(x, 2.0 * x + 1.0) for x in range(10)]           # y = 2x + 1 exact
        r = learn_elasticity(pairs)
        self.assertAlmostEqual(r["a"], 2.0, places=5)
        self.assertAlmostEqual(r["b"], 1.0, places=5)
        self.assertAlmostEqual(r["r2"], 1.0, places=5)


if __name__ == "__main__":
    unittest.main()
