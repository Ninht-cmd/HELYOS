"""CriticalPropertyAnalyzer : découverte STRUCTURELLE des propriétés critiques (AST).

Les cinq cas d'acceptation fixés par le Conservateur :
  CAS 1  GR-2 dans governance/           → propriété détectée
  CAS 2  même logique dans world/toolbus → propriété TOUJOURS détectée (indépendant du chemin)
  CAS 3  token dans string / commentaire → aucune propriété
  CAS 4  chemin sensible sans gouvernance → CRITICAL_BYPASS_FOUND
  CAS 5  mutation du chemin de validation → les tests doivent tuer le mutant
"""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from jarvis_kernel.world.critical_property import (analyze_file, analyze_source, critical_targets,
                                                   has_bypass)
from jarvis_kernel.world.mutation_testing import run_mutation_testing

ROOT = Path(__file__).resolve().parents[1]
POLICY = ROOT / "src" / "jarvis_kernel" / "governance" / "policy.py"


class TestCas1RealGovernance(unittest.TestCase):
    def test_detects_gr2_and_deny_in_real_policy(self) -> None:
        props = analyze_file(POLICY)
        mv = [p for p in props if p.kind == "mandatory_validation"]
        require = [p for p in mv if p.required_outcome == "REQUIRE_VALIDATION"]
        deny = [p for p in mv if p.required_outcome == "DENY"]
        self.assertTrue(require, "GR-2/GR-7 (REQUIRE_VALIDATION) doivent être découverts")
        self.assertTrue(deny, "GR-1/GR-3 (DENY) doivent être découverts")
        # la propriété GR-2 est gardée par une condition de validation, preuve = control-flow
        gr2 = next(p for p in require if "validated" in " ".join(p.guards))
        self.assertEqual(gr2.criticality, "CRITICAL")
        self.assertTrue(any("control-flow" in e for e in gr2.evidence))


class TestCas2MovedOutOfGovernance(unittest.TestCase):
    def test_same_logic_in_toolbus_still_critical(self) -> None:
        src = (
            "def guard(action, governance):\n"
            "    if action.sensitive:\n"
            "        verdict = governance.submit(action)\n"
            "        if verdict.decision == Decision.REQUIRE_VALIDATION:\n"
            "            return stop()\n"
            "    return proceed()\n"
        )
        props = analyze_source(src, "world/toolbus.py")            # chemin HORS governance/
        self.assertTrue(any(p.kind == "mandatory_validation" for p in props))
        self.assertTrue(any(p.kind == "governance_gate" for p in props))
        self.assertFalse(has_bypass(props))                        # il Y A un gate → pas un bypass


class TestCas3TokensAreNotProperties(unittest.TestCase):
    def test_string_and_comment_produce_nothing(self) -> None:
        src = (
            "def helper():\n"
            '    message = "REQUIRE_VALIDATION"   # REQUIRE_VALIDATION doit être géré ici\n'
            "    return message\n"
        )
        self.assertEqual(analyze_source(src, "world/x.py"), [])

    def test_enum_in_fstring_is_a_message_not_a_decision(self) -> None:
        # référencer l'enum dans une f-string de log ne doit pas créer de propriété critique
        src = ('def f(action):\n'
               '    if action.sensitive:\n'
               '        return log(f"décision {Decision.REQUIRE_VALIDATION}")\n')
        props = analyze_source(src, "world/x.py")
        self.assertFalse(any(p.kind == "mandatory_validation" for p in props))


class TestCas4Bypass(unittest.TestCase):
    def test_sensitive_effect_without_governance_is_bypass(self) -> None:
        src = (
            "def run_external(action, connector):\n"
            "    if action.sensitive:\n"
            "        return connector.execute(action)\n"
        )
        props = analyze_source(src, "world/toolbus.py")
        self.assertTrue(has_bypass(props))
        bypass = next(p for p in props if p.kind == "critical_bypass")
        self.assertEqual(bypass.criticality, "CRITICAL")
        self.assertIn("execute", bypass.protected_effect)

    def test_gate_present_is_not_bypass(self) -> None:
        src = (
            "def run_external(action, connector, governance):\n"
            "    if action.sensitive:\n"
            "        v = governance.submit(action)\n"
            "        return connector.execute(action) if v.ok else None\n"
        )
        self.assertFalse(has_bypass(analyze_source(src, "world/toolbus.py")))


_GOV = '''\
from enum import Enum


class Decision(Enum):
    ALLOW = "allow"
    REQUIRE_VALIDATION = "require_validation"


class Action:
    def __init__(self, sensitive=False):
        self.sensitive = sensitive


def gate(action):
    if action.sensitive:
        return Decision.REQUIRE_VALIDATION
    return Decision.ALLOW
'''

_TEST = '''\
import unittest

from gov import Action, Decision, gate


class T(unittest.TestCase):
    def test_sensitive_requires_validation(self):
        self.assertEqual(gate(Action(sensitive=True)), Decision.REQUIRE_VALIDATION)

    def test_normal_allows(self):
        self.assertEqual(gate(Action(sensitive=False)), Decision.ALLOW)
'''


class TestCas5MutationOfProperty(unittest.TestCase):
    def test_property_derived_target_mutation_is_killed(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "src").mkdir(); (root / "tests").mkdir()
            gov = root / "src" / "gov.py"
            gov.write_text(_GOV, encoding="utf-8")
            (root / "tests" / "test_gov.py").write_text(_TEST, encoding="utf-8")

            # la CIBLE de mutation vient de l'ANALYSE de propriété, pas d'un scan de marqueurs
            props = analyze_file(gov)
            targets = critical_targets(props)
            self.assertTrue(targets, "la propriété doit fournir une ligne à muter")
            rep = run_mutation_testing(root / "src", root / "tests", targets, pattern="test_gov.py")
            self.assertTrue(rep.findings)
            self.assertFalse(rep.critical_survivors)               # le test tue la mutation du chemin
            self.assertEqual(rep.mutation_score, 1.0)


if __name__ == "__main__":
    unittest.main()
