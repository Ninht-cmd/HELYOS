"""Tests du moteur d'analyse AST : findings avec preuve (déterministes) + intégration réelle."""

from __future__ import annotations

import unittest
from pathlib import Path

from jarvis_kernel.world.ast_analysis import (AstIndex, analyze, analyze_repo,
                                              test_coverage_gaps)

ROOT = Path(__file__).resolve().parents[3]


class TestAnalyzers(unittest.TestCase):
    def test_complexity(self) -> None:
        idx = AstIndex()
        idx.add("m", "def f(a):\n if a: pass\n if a: pass\n if a: pass\n")
        self.assertEqual(idx.modules["m"].functions[0].complexity, 4)   # 1 + 3 if

    def test_deadcode_context_aware(self) -> None:
        idx = AstIndex()
        idx.add("jarvis_kernel.api.routes",
                "import x\n@x.get\ndef handler(): pass\ndef orphan(): pass\ndef used(): pass\nused()\n")
        dead = {f.symbol for f in analyze(idx) if f.category == "dead_code"}
        self.assertIn("orphan", dead)
        self.assertNotIn("handler", dead)      # décoré (route) -> pas mort
        self.assertNotIn("used", dead)         # référencé -> pas mort

    def test_architecture_invariant_violation(self) -> None:
        idx = AstIndex()
        idx.add("jarvis_kernel.governance.policy", "from ..agents import foo\nfoo\n")
        idx.add("jarvis_kernel.agents", "def foo(): pass\n")
        viol = [f for f in analyze(idx) if f.category == "architecture"]
        self.assertTrue(viol)
        self.assertIn("governance", viol[0].evidence[0])

    def test_broken_import(self) -> None:
        idx = AstIndex()
        idx.add("jarvis_kernel.world.foo", "from .nope import Bar\n")
        self.assertTrue(any(f.category == "broken_import" for f in analyze(idx)))

    def test_import_cycle(self) -> None:
        idx = AstIndex()
        idx.add("jarvis_kernel.a", "from .b import X\nX\n")
        idx.add("jarvis_kernel.b", "from .a import Y\nY\n")
        self.assertTrue(any(f.category == "import_cycle" for f in analyze(idx)))

    def test_untested_mapping(self) -> None:
        src = AstIndex(); src.add("jarvis_kernel.foo", "def compute(): pass\n")
        no = AstIndex(); no.add("test_bar", "def test(): pass\n")
        self.assertTrue(any(f.symbol == "compute" for f in test_coverage_gaps(src, no)))
        yes = AstIndex(); yes.add("test_foo", "from jarvis_kernel.foo import compute\ncompute()\n")
        self.assertFalse(any(f.symbol == "compute" for f in test_coverage_gaps(src, yes)))


class TestRealRepo(unittest.TestCase):
    def test_analyzes_own_codebase(self) -> None:
        findings = analyze_repo(ROOT)
        self.assertGreater(len(findings), 0)
        cats = {f.category for f in findings}
        self.assertTrue({"dead_code", "untested", "complexity"} & cats)

    def test_layer_invariants_hold_and_no_false_dead_route(self) -> None:
        findings = analyze_repo(ROOT)
        self.assertEqual([f for f in findings if f.category == "architecture"], [])  # invariants OK
        self.assertEqual([f for f in findings if f.category == "broken_import"], [])  # 0 import cassé
        dead = {f.symbol for f in findings if f.category == "dead_code"}
        self.assertNotIn("cockpit_topology", dead)     # handler FastAPI décoré -> pas mort


if __name__ == "__main__":
    unittest.main()
