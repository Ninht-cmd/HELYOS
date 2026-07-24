"""Tests du registre de modules à interrupteur (on/off, anti-saturation)."""

from __future__ import annotations

import time
import unittest

from jarvis_kernel.context import build_default_context
from jarvis_kernel.integrations.modules import DEFAULTS, ModuleRegistry


class TestModules(unittest.TestCase):
    def setUp(self) -> None:
        self.ctx = build_default_context()
        self.reg = ModuleRegistry(self.ctx.memory)

    def test_defaults_and_toggle_persist(self) -> None:
        self.assertTrue(self.reg.is_on("market"))          # on par défaut
        self.assertFalse(self.reg.is_on("anythingllm"))    # off par défaut
        self.reg.toggle("anythingllm", True)
        self.assertTrue(self.reg.is_on("anythingllm"))
        # persiste : un nouveau registre sur la même mémoire voit l'état
        self.assertTrue(ModuleRegistry(self.ctx.memory).is_on("anythingllm"))

    def test_unknown_module_rejected(self) -> None:
        with self.assertRaises(KeyError):
            self.reg.toggle("licorne", True)

    def test_summary_counts_active(self) -> None:
        s = self.reg.summary()
        self.assertEqual(s["total"], len(DEFAULTS))
        self.assertGreaterEqual(s["actifs"], 1)

    def test_market_off_stops_pulse_network(self) -> None:
        # anti-saturation : marché éteint -> le veilleur marché ne renvoie rien
        self.reg.toggle("market", False)
        # neutralise les autres connecteurs réseau du test
        self.ctx.connectors = []
        items = self.ctx.pulse._watch_market()
        self.assertEqual(items, [])

    def test_jarvis_toggle_via_chat(self) -> None:
        j = self.ctx.jarvis
        self.assertEqual(j.classify("mes modules"), "modules")
        self.assertEqual(j.classify("active AnythingLLM"), "modules")
        r = j.handle("active AnythingLLM")
        self.assertEqual(r.intent, "modules")
        self.assertIn("allumé", r.text)
        self.assertTrue(self.reg.is_on("anythingllm"))
        r2 = j.handle("éteins le marché")
        self.assertIn("éteint", r2.text)
        self.assertFalse(self.reg.is_on("market"))

    def test_local_module_launch_hint_on_enable(self) -> None:
        r = self.ctx.jarvis.handle("active dolibarr")
        self.assertIn("démarrer", r.text.lower())          # dit comment le lancer
        self.assertIn("docker", r.text.lower())


if __name__ == "__main__":
    unittest.main()
