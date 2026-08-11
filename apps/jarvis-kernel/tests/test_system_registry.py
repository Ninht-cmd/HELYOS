"""SystemRegistry + BrickRegistry : la vérité opérationnelle sondée en direct.

Cœur de la règle « zéro coquille vide » : ces tests VERROUILLENT l'invariant — une brique
n'est jamais ACTIVE sans preuve runtime (moteur/API/donnée), les briques non construites sont
MISSING (pas ACTIVE), et une source clonée n'est jamais ACTIVE. Les sondes doivent aussi être
gracieuses (aucun outil requis) : ces tests tournent en CI Linux sans Ollama/Docker/NVIDIA."""

from __future__ import annotations

import unittest

from fastapi.testclient import TestClient

from jarvis_kernel.context import build_default_context
from jarvis_kernel.integrations.system_registry import (ACTIVE, MISSING, STATUSES, build_registry)
from jarvis_kernel.main import create_app


class TestSystemRegistry(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.reg = build_registry(build_default_context())
        cls.byid = {b["id"]: b for b in cls.reg["bricks"]}

    def test_all_statuses_are_valid(self) -> None:
        for b in self.reg["bricks"]:
            self.assertIn(b["status"], STATUSES, b["id"])

    def test_never_active_without_runtime_proof(self) -> None:
        # LA règle : jamais ACTIVE sans moteur/API/donnée réelle
        for b in self.reg["bricks"]:
            if b["status"] == ACTIVE:
                self.assertTrue(b["engine"] or b["api"] or b["real_data"],
                                f"{b['id']} marqué ACTIVE sans preuve")

    def test_unbuilt_bricks_are_missing_not_active(self) -> None:
        for bid in ("payment_connector", "marketing", "sav", "rh", "administration"):
            self.assertEqual(self.byid[bid]["status"], MISSING, bid)

    def test_built_control_bricks_are_active(self) -> None:
        # machine à états + gate + IAM existent réellement (moteur + tests) → ACTIVE, pas une carte
        for bid in ("manual_override", "safe_mode", "iam"):
            self.assertEqual(self.byid[bid]["status"], ACTIVE, bid)
            self.assertTrue(self.byid[bid]["engine"])

    def test_source_only_engines_never_active(self) -> None:
        # TensorRT-LLM / Triton / NeMo = source clonée -> jamais ACTIVE (pas de moteur construit)
        for bid in ("tensorrt_llm", "triton", "nemo"):
            self.assertNotEqual(self.byid[bid]["status"], ACTIVE, bid)

    def test_helyos_core_active(self) -> None:
        self.assertEqual(self.byid["governance"]["status"], ACTIVE)
        self.assertEqual(self.byid["engineering_brain"]["status"], ACTIVE)
        self.assertEqual(self.byid["cockpit"]["status"], ACTIVE)

    def test_node_cockpit_is_reference_never_source_of_truth(self) -> None:
        node = self.byid["node_cockpit"]
        self.assertEqual(node["category"], "reference")
        self.assertNotEqual(node["status"], ACTIVE)          # données figées -> jamais ACTIVE

    def test_endpoint_and_overall_bounded(self) -> None:
        d = TestClient(create_app()).get("/os/registry").json()
        self.assertTrue(0 <= d["overall"] <= 100)
        self.assertIn("categories", d)
        self.assertGreaterEqual(len(d["bricks"]), 10)


if __name__ == "__main__":
    unittest.main()
