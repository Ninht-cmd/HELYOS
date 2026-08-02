"""Tests de la gouvernance des modèles (MLOps du World Model) : versioning append-only,
promotion sous garde, rollback, dérive, provenance."""

from __future__ import annotations

import random
import unittest

from jarvis_kernel.world.learning import CausalLaw
from jarvis_kernel.world.registry import ModelRegistry

TRUTH = 1.6


def _counter():
    """Horloge déterministe (pas de dépendance au temps réel dans les tests)."""
    t = [0.0]
    def clock():
        t[0] += 1.0
        return t[0]
    return clock


def _fit(coef_target: float, seed: int, n: int = 200, noise: float = 0.3) -> CausalLaw:
    """Renvoie une loi entraînée dont le coefficient tend vers coef_target."""
    law = CausalLaw("cout~prix", "sup.prix", "prod.cout", coef_mean=1.0, coef_sigma=1.0, noise_sigma=noise)
    rng = random.Random(seed)
    for _ in range(n):
        x = rng.uniform(1.0, 6.0)
        law.observe(x, coef_target * x + rng.gauss(0, noise))
    return law


def _valset(seed: int, n: int = 200, noise: float = 0.2):
    rng = random.Random(seed)
    return [(x, TRUTH * x + rng.gauss(0, noise)) for x in (rng.uniform(1.0, 6.0) for _ in range(n))]


class TestVersioning(unittest.TestCase):
    def test_append_only_history_and_active(self) -> None:
        reg = ModelRegistry(clock=_counter())
        reg.register(_fit(1.42, seed=1), note="v1")
        reg.register(_fit(1.58, seed=2), note="v2")
        h = reg.history("cout~prix")
        self.assertEqual([v.version for v in h], [1, 2])            # historique conservé
        self.assertEqual(reg.active_version("cout~prix").version, 2)


class TestGuardedPromotion(unittest.TestCase):
    def setUp(self) -> None:
        self.reg = ModelRegistry(clock=_counter())
        self.val = _valset(seed=99)

    def test_better_challenger_is_promoted(self) -> None:
        self.reg.register(_fit(1.40, seed=1), note="champion faible", metrics={"rmse": 999})
        # en réalité on enregistre les métriques réelles : re-calons le champion proprement
        champ = _fit(1.40, seed=1)
        self.reg = ModelRegistry(clock=_counter())
        from jarvis_kernel.world.learning import calibration
        self.reg.register(champ, note="champion", metrics=calibration(champ, self.val))
        r = self.reg.propose(_fit(1.60, seed=2), self.val, note="mieux entraîné")
        self.assertEqual(r["decision"], "promoted")                 # meilleur -> activé
        self.assertEqual(self.reg.active_version("cout~prix").version, 2)

    def test_worse_challenger_is_rejected_champion_kept(self) -> None:
        from jarvis_kernel.world.learning import calibration
        champ = _fit(1.60, seed=2)
        self.reg.register(champ, note="bon champion", metrics=calibration(champ, self.val))
        # challenger entraîné sur des données CORROMPUES (coef ~2.6) -> pire sur la validation
        r = self.reg.propose(_fit(2.6, seed=7), self.val, note="données corrompues")
        self.assertEqual(r["decision"], "rejected")                 # pas d'amélioration -> refusé
        self.assertEqual(self.reg.active_version("cout~prix").version, 1)   # champion conservé
        self.assertGreater(r["challenger"]["rmse"], r["champion"]["rmse"])


class TestRollback(unittest.TestCase):
    def test_rollback_restores_earlier_version(self) -> None:
        reg = ModelRegistry(clock=_counter())
        reg.register(_fit(1.58, seed=1), note="v1")
        reg.register(_fit(2.6, seed=2), note="v2 douteuse")
        self.assertEqual(reg.active_version("cout~prix").version, 2)
        reg.rollback("cout~prix", 1, reason="série v2 corrompue")
        self.assertEqual(reg.active_version("cout~prix").version, 1)
        self.assertEqual(len(reg.history("cout~prix")), 2)          # historique intact
        self.assertEqual(reg.audit[-1].action, "rollback")


class TestDriftAndProvenance(unittest.TestCase):
    def test_drift_flagged_on_degraded_data(self) -> None:
        from jarvis_kernel.world.learning import calibration
        reg = ModelRegistry(clock=_counter())
        law = _fit(1.60, seed=1)
        val = _valset(seed=5)
        reg.register(law, note="modèle sain", metrics=calibration(law, val))
        # données récentes issues d'un monde qui a changé (coef réel devenu 2.4)
        rng = random.Random(3)
        drifted = [(x, 2.4 * x + rng.gauss(0, 0.2)) for x in (rng.uniform(1, 6) for _ in range(150))]
        d = reg.drift("cout~prix", drifted)
        self.assertTrue(d["drifted"])                               # la dérive est détectée
        self.assertGreater(d["ratio"], 1.5)

    def test_explain_reports_provenance(self) -> None:
        reg = ModelRegistry(clock=_counter())
        val = _valset(seed=8)
        from jarvis_kernel.world.learning import calibration
        c = _fit(1.40, seed=1)
        reg.register(c, note="champion", metrics=calibration(c, val))
        reg.propose(_fit(1.60, seed=2), val, note="ré-entraînement")
        txt = reg.explain("cout~prix")
        self.assertIn("Passé de", txt)                              # explique le changement
        self.assertIn("Provenance", txt)


if __name__ == "__main__":
    unittest.main()
