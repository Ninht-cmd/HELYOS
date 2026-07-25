"""Tests ingénierie : pièces 3D STL valides + calculs méca (Python pur)."""

from __future__ import annotations

import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from jarvis_kernel.integrations.engineering import generate_part, mechanical


class TestEngineering(unittest.TestCase):
    def test_box_stl_is_valid(self) -> None:
        with TemporaryDirectory() as td:
            r = generate_part("box", {"l": 40, "d": 20, "h": 10}, out_dir=td)
            self.assertEqual(r["triangles"], 12)             # une boîte = 12 triangles
            stl = Path(r["path"]).read_text()
            self.assertTrue(stl.startswith("solid"))
            self.assertTrue(stl.strip().endswith("endsolid helyos_box"))
            self.assertEqual(stl.count("facet normal"), 12)  # STL structurellement correct

    def test_gear_has_teeth(self) -> None:
        with TemporaryDirectory() as td:
            r = generate_part("engrenage", {"dents": 12, "h": 6, "r": 20}, out_dir=td)
            self.assertEqual(r["kind"], "engrenage")
            self.assertGreater(r["triangles"], 100)          # profil denté = beaucoup de triangles

    def test_cylinder(self) -> None:
        with TemporaryDirectory() as td:
            r = generate_part("cylindre", {"r": 15, "h": 30}, out_dir=td)
            self.assertGreater(r["triangles"], 40)

    def test_gear_ratio(self) -> None:
        r = mechanical("engrenage", {"z1": 12, "z2": 36})
        self.assertEqual(r["ratio"], 3.0)

    def test_beam_deflection(self) -> None:
        r = mechanical("poutre", {"F": 100, "L": 1, "E": 210e9, "I": 1e-8})
        self.assertIn("fleche_m", r)
        self.assertGreater(r["fleche_m"], 0)


class TestBrainEngineeringTools(unittest.TestCase):
    def test_brain_has_engineering_tools(self) -> None:
        from jarvis_kernel.agents.reasoning import ReasoningAgent
        from jarvis_kernel.context import build_default_context
        agent = ReasoningAgent(build_default_context())
        self.assertIn("calcul_meca", agent._tools)
        self.assertIn("piece_3d", agent._tools)
        self.assertIn("piece_3d", agent._actions)            # génère un fichier -> A2
        self.assertNotIn("calcul_meca", agent._actions)      # calcul = lecture A1

    def test_kv_parser(self) -> None:
        from jarvis_kernel.agents.reasoning import ReasoningAgent
        kind, params = ReasoningAgent._kv("engrenage dents=12 h=6")
        self.assertEqual(kind, "engrenage")
        self.assertEqual(params, {"dents": "12", "h": "6"})


if __name__ == "__main__":
    unittest.main()
