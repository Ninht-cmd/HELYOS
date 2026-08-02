"""Tests du Supply Chain OS : science des stocks validée, Monte-Carlo auto-cohérent,
politique de bout en bout, et la boucle apprentissage + gouvernance du délai réel."""

from __future__ import annotations

import random
import unittest

from jarvis_kernel.world.domains import validate_domain
from jarvis_kernel.world.domains.supply_chain import (SUPPLY_CHAIN, eoq, inventory_policy,
                                                      lead_time_demand_std, normal_loss,
                                                      reorder_point, safety_stock,
                                                      service_level_z, simulate_service_level)
from jarvis_kernel.world.learning import CausalLaw, calibration
from jarvis_kernel.world.registry import ModelRegistry


class TestInventoryScience(unittest.TestCase):
    def test_reference_cases_pass(self) -> None:
        r = validate_domain(SUPPLY_CHAIN)
        self.assertEqual(r["passes"], r["total"])
        self.assertGreaterEqual(r["total"], 4)

    def test_eoq_and_safety_stock(self) -> None:
        self.assertAlmostEqual(eoq(1000, 50, 2), 223.607, places=2)
        self.assertAlmostEqual(safety_stock(service_level_z(0.95), 100), 164.485, places=2)

    def test_dlt_std_combines_both_uncertainties(self) -> None:
        # d=10, σ_d=2, LT=9, σ_LT=1  -> √(9·4 + 100·1) = √136 = 11.66
        self.assertAlmostEqual(lead_time_demand_std(10, 2, 9, 1), 136 ** 0.5, places=4)


class TestMonteCarloConsistency(unittest.TestCase):
    def test_reorder_point_delivers_target_service(self) -> None:
        # politique à 95% : le MC doit retrouver ~95% de service (auto-cohérence)
        mean_dlt, sigma_dlt = 90.0, 11.66
        rop = mean_dlt + service_level_z(0.95) * sigma_dlt
        sim = simulate_service_level(mean_dlt, sigma_dlt, rop, n=20000, seed=1)
        self.assertAlmostEqual(sim["service_level"], 0.95, delta=0.02)


class TestEndToEndPolicy(unittest.TestCase):
    def test_policy_is_complete_and_coherent(self) -> None:
        p = inventory_policy(demand=10, sigma_demand=2, lead_time=9, sigma_lead_time=1,
                             service_level=0.95, annual_demand=3650, order_cost=50, holding_cost=2,
                             stockout_cost=20)
        for k in ("sigma_dlt", "z", "safety_stock", "reorder_point", "eoq", "fill_rate", "total_cost"):
            self.assertIn(k, p)
        self.assertGreater(p["reorder_point"], p["safety_stock"])   # ROP = demande×délai + SS
        self.assertTrue(0.9 < p["fill_rate"] <= 1.0)


class TestLearningAndGovernance(unittest.TestCase):
    """Le délai réel est APPRIS ; les versions de la loi sont GOUVERNÉES."""

    def _lt_stream(self, mean, seed, n=150, noise=1.0):
        rng = random.Random(seed)
        return [(1.0, rng.gauss(mean, noise)) for _ in range(n)]     # x=1 -> loi constante = délai moyen

    def test_learned_lead_time_updates_policy_and_registry(self) -> None:
        # a priori : on croit le fournisseur à 6 j ; en réalité il est à 9 j.
        law = CausalLaw("lead_time", "sup.one", "sup.lead_time", coef_mean=6.0, coef_sigma=3.0, noise_sigma=1.0)
        val = self._lt_stream(9.0, seed=100)
        reg = ModelRegistry()
        reg.register(law, note="a priori 6 j", metrics=calibration(law, val))
        rop_before = reorder_point(10, law.coef_mean, safety_stock(service_level_z(0.95),
                                   lead_time_demand_std(10, 2, law.coef_mean, 1)))

        learned = CausalLaw("lead_time", "sup.one", "sup.lead_time", 6.0, 3.0, 1.0)
        for x, y in self._lt_stream(9.0, seed=7):
            learned.observe(x, y)
        self.assertAlmostEqual(learned.coef_mean, 9.0, delta=0.5)    # délai réel appris

        r = reg.propose(learned, val, note="calibré sur 150 réceptions")
        self.assertEqual(r["decision"], "promoted")                  # meilleur -> activé
        rop_after = reorder_point(10, learned.coef_mean, safety_stock(service_level_z(0.95),
                                  lead_time_demand_std(10, 2, learned.coef_mean, 1)))
        self.assertGreater(rop_after, rop_before)                    # on recommande plus tôt (délai plus long)


if __name__ == "__main__":
    unittest.main()
