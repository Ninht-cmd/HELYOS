"""Tests de la boucle d'apprentissage : le modèle se corrige des résultats réels."""

from __future__ import annotations

import random
import unittest

from jarvis_kernel.world.learning import (CausalLaw, calibration, close_loop,
                                          relearn, wire_learned)
from jarvis_kernel.world.ontology import KnowledgeGraph, default_ontology

NOW = 1_000_000.0
TRUTH = 1.6            # coefficient causal réel (caché du modèle)


def _stream(n: int, seed: int, noise: float = 0.3):
    rng = random.Random(seed)
    return [(x, TRUTH * x + rng.gauss(0, noise))
            for x in (rng.uniform(1.0, 6.0) for _ in range(n))]


class TestBayesianUpdate(unittest.TestCase):
    def test_converges_to_truth(self) -> None:
        law = CausalLaw("coût~prix", "sup.prix", "prod.cout", coef_mean=1.0, coef_sigma=1.0, noise_sigma=0.3)
        for x, y in _stream(300, seed=1):
            law.observe(x, y)
        self.assertAlmostEqual(law.coef_mean, TRUTH, delta=0.05)   # a apprend la vérité
        self.assertLess(law.coef_sigma, 0.05)                      # incertitude resserrée

    def test_uncertainty_monotonically_shrinks(self) -> None:
        law = CausalLaw("l", "x", "y", coef_mean=1.0, coef_sigma=2.0, noise_sigma=0.3)
        prev = law.coef_sigma
        for x, y in _stream(30, seed=2):
            law.observe(x, y)
            self.assertLessEqual(law.coef_sigma, prev + 1e-9)      # jamais plus incertain
            prev = law.coef_sigma

    def test_predict_uncertainty_has_two_sources(self) -> None:
        law = CausalLaw("l", "x", "y", coef_mean=1.6, coef_sigma=0.1, noise_sigma=0.3)
        _, sigma = law.predict(4.0)
        # σ² = (4·0.1)² + 0.3² = 0.16 + 0.09 = 0.25 -> σ = 0.5
        self.assertAlmostEqual(sigma, 0.5, places=6)


class TestCalibration(unittest.TestCase):
    def test_coverage_reasonable_after_learning(self) -> None:
        law = CausalLaw("l", "x", "y", coef_mean=1.0, coef_sigma=1.0, noise_sigma=0.3)
        for x, y in _stream(300, seed=3):
            law.observe(x, y)
        c = calibration(law, _stream(200, seed=99))
        self.assertLess(c["mae"], 0.4)                             # erreur ~ niveau du bruit
        self.assertGreater(c["coverage"], 0.4)                     # la bande ±1σ couvre le réel
        self.assertLess(abs(c["bias"]), 0.15)                      # peu de biais systématique


class TestClosedLoop(unittest.TestCase):
    def test_error_decreases_as_model_learns(self) -> None:
        law = CausalLaw("l", "x", "y", coef_mean=1.0, coef_sigma=1.0, noise_sigma=0.3)
        traj = close_loop(law, _stream(200, seed=4))
        first = sum(abs(t["erreur"]) for t in traj[:40]) / 40      # erreur au début (mauvais coef)
        last = sum(abs(t["erreur"]) for t in traj[-40:]) / 40      # erreur à la fin (coef appris)
        self.assertLess(last, first)                               # la boucle RÉDUIT l'erreur
        self.assertAlmostEqual(traj[-1]["coef"], TRUTH, delta=0.06)


class TestGraphSelfCorrection(unittest.TestCase):
    def test_relearn_updates_the_world_model(self) -> None:
        g = KnowledgeGraph(default_ontology())
        g.add_entity("Supplier", "sup", now=NOW, values={"unit_price": 5.0})
        g.add_entity("Product", "prod", now=NOW, values={"unites_mois": 100})
        law = CausalLaw("coût", g.key("sup", "unit_price"), g.key("prod", "cout_unitaire"),
                        coef_mean=1.0, coef_sigma=1.0, noise_sigma=0.3)
        wire_learned(g, law)
        before = g.value("prod", "cout_unitaire")                  # 1.0 × 5 = 5.0 (modèle naïf)
        self.assertAlmostEqual(before, 5.0, places=3)
        relearn(g, law, _stream(300, seed=5))                      # apprend des résultats réels
        after = g.value("prod", "cout_unitaire")                   # ≈ 1.6 × 5 = 8.0 (corrigé)
        self.assertAlmostEqual(after, TRUTH * 5.0, delta=0.4)
        self.assertGreater(after, before)


if __name__ == "__main__":
    unittest.main()
