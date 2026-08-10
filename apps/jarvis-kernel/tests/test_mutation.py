"""Mutation testing ciblé : les tests SAVENT-ILS détecter une ligne critique fausse ?

- Unitaires : opérateurs de mutation GR-2, portail (la mutation ne peut que DÉGRADER un
  verdict), facteur mutation dans change_assurance.
- Acceptation (sous-processus réels) : scénario en deux temps —
    A) test faible (exécute la ligne GR-2 sans asserter sa valeur) : diff/CI/comportement
       verts MAIS le mutant REQUIRE_VALIDATION→ALLOW SURVIT → NOT_CONFIRMED ;
    B) test ciblé ajouté : le même mutant est TUÉ → CHANGE_CONFIRMED.
  Preuve : le test n'exécute plus seulement la ligne, il détecte qu'elle est fausse.
"""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from jarvis_kernel.world.confidence import change_assurance
from jarvis_kernel.world.diff_coverage import (CHANGE_BROKEN, CHANGE_CONFIRMED,
                                               CHANGE_NOT_SUFFICIENTLY_VALIDATED)
from jarvis_kernel.world.mutation_testing import (KILLED, SURVIVED, MutationFinding, MutationReport,
                                                  critical_targets_in_file, gated_change_verdict,
                                                  generate_mutants, run_mutation_testing)

_GOV = '''\
def classify(action, sensitive=False):
    if action == "external" or sensitive:  # GR-2
        return "require_validation"
    return "allow"
'''

_TEST_WEAK = '''\
import unittest

from gov import classify


class T(unittest.TestCase):
    def test_returns_a_string(self):
        self.assertIsInstance(classify("external"), str)   # exécute la ligne, n'assert pas la valeur

    def test_read_allows(self):
        self.assertEqual(classify("read"), "allow")
'''

_TEST_STRONG = _TEST_WEAK + '''
    def test_external_requires_validation(self):
        self.assertEqual(classify("external"), "require_validation")
'''


def _tree(root: Path, test_src: str) -> Path:
    (root / "src").mkdir(parents=True, exist_ok=True)
    (root / "tests").mkdir(parents=True, exist_ok=True)
    (root / "src" / "gov.py").write_text(_GOV, encoding="utf-8")
    (root / "tests" / "test_gov.py").write_text(test_src, encoding="utf-8")
    return root


class TestOperators(unittest.TestCase):
    def test_value_swap(self) -> None:
        ops = dict(generate_mutants('        return "require_validation"'))
        self.assertIn("require_validation_to_allow", ops)
        self.assertIn('"allow"', ops["require_validation_to_allow"])

    def test_condition_negation_preserves_comment(self) -> None:
        ops = dict(generate_mutants('    if action == "external" or sensitive:  # GR-2'))
        self.assertIn("negate_condition", ops)
        self.assertIn("not (", ops["negate_condition"])
        self.assertIn("# GR-2", ops["negate_condition"])

    def test_no_mutant_for_neutral_line(self) -> None:
        self.assertEqual(generate_mutants("    x = compute_total(items)"), [])

    def test_comment_tokens_are_not_mutated(self) -> None:
        # un token de gouvernance dans un COMMENTAIRE ne doit produire aucun mutant
        # (mutation équivalente = survivant garanti qui bloquerait CONFIRMED à tort)
        self.assertEqual(generate_mutants("    total = 0  # REQUIRE_VALIDATION géré ailleurs"), [])
        # mais la vraie valeur de retour, elle, est bien mutée
        ops = dict(generate_mutants('        return "require_validation"  # GR-2'))
        self.assertIn("require_validation_to_allow", ops)
        self.assertTrue(ops["require_validation_to_allow"].endswith("# GR-2"))   # commentaire préservé


class TestGate(unittest.TestCase):
    def _survivor(self, crit):
        return MutationFinding(target="gov.py:3", mutation_operator="require_validation_to_allow",
                               original='return "require_validation"', mutated='return "allow"',
                               tests_run=["test_x"], result=SURVIVED, criticality=crit,
                               confidence=0.4, hypotheses=["test insuffisant"])

    def test_critical_survivor_downgrades_confirmed(self) -> None:
        rep = MutationReport([self._survivor(1.0)])
        self.assertFalse(rep.confirmed_ok)
        self.assertEqual(gated_change_verdict(CHANGE_CONFIRMED, rep), CHANGE_NOT_SUFFICIENTLY_VALIDATED)

    def test_non_critical_survivor_does_not_block(self) -> None:
        rep = MutationReport([self._survivor(0.3)])
        self.assertTrue(rep.confirmed_ok)
        self.assertEqual(gated_change_verdict(CHANGE_CONFIRMED, rep), CHANGE_CONFIRMED)

    def test_gate_never_upgrades_or_rescues_broken(self) -> None:
        clean = MutationReport([])                              # aucun mutant → score 1.0
        self.assertEqual(gated_change_verdict(CHANGE_BROKEN, clean), CHANGE_BROKEN)  # ne sauve pas une CI rouge
        self.assertEqual(gated_change_verdict(CHANGE_NOT_SUFFICIENTLY_VALIDATED, clean),
                         CHANGE_NOT_SUFFICIENTLY_VALIDATED)     # ne promeut pas


class TestChangeAssuranceMutationFactor(unittest.TestCase):
    def test_default_is_neutral(self) -> None:
        self.assertEqual(change_assurance(True, 1.0, 1.0, True, 0.9),
                         change_assurance(True, 1.0, 1.0, True, 0.9, mutation_score=1.0))

    def test_low_mutation_score_drags_assurance_down(self) -> None:
        self.assertLess(change_assurance(True, 1.0, 1.0, True, 1.0, mutation_score=0.3),
                        change_assurance(True, 1.0, 1.0, True, 1.0, mutation_score=1.0))
        self.assertEqual(change_assurance(True, 1.0, 1.0, True, 1.0, mutation_score=0.0), 0.0)


class TestAcceptanceSurvivorThenKilled(unittest.TestCase):
    def test_weak_test_lets_mutant_survive_then_targeted_test_kills_it(self) -> None:
        # ---- A : test faible ----
        with tempfile.TemporaryDirectory() as td:
            root = _tree(Path(td), _TEST_WEAK)
            targets = critical_targets_in_file(root / "src" / "gov.py")
            self.assertTrue(any(ln == 3 for _f, ln, _c in targets))     # la ligne require_validation ciblée
            rep_a = run_mutation_testing(root / "src", root / "tests", targets, pattern="test_gov.py")
            self.assertTrue(rep_a.critical_survivors, "un mutant critique doit survivre au test faible")
            surv = rep_a.critical_survivors[0]
            self.assertEqual(surv.result, SURVIVED)
            self.assertTrue(surv.hypotheses)                            # hypothèses, PAS « bug confirmé »
            self.assertLess(surv.confidence, 0.5)
            self.assertFalse(rep_a.confirmed_ok)
            # même avec diff/CI/comportement verts, le portail dégrade :
            self.assertEqual(gated_change_verdict(CHANGE_CONFIRMED, rep_a),
                             CHANGE_NOT_SUFFICIENTLY_VALIDATED)

        # ---- B : test ciblé ajouté ----
        with tempfile.TemporaryDirectory() as td:
            root = _tree(Path(td), _TEST_STRONG)
            targets = critical_targets_in_file(root / "src" / "gov.py")
            rep_b = run_mutation_testing(root / "src", root / "tests", targets, pattern="test_gov.py")
            self.assertTrue(rep_b.findings)
            self.assertFalse(rep_b.critical_survivors, "le test ciblé doit tuer le mutant GR-2")
            self.assertEqual(rep_b.mutation_score, 1.0)
            self.assertTrue(all(f.result == KILLED for f in rep_b.findings))
            self.assertEqual(gated_change_verdict(CHANGE_CONFIRMED, rep_b), CHANGE_CONFIRMED)


if __name__ == "__main__":
    unittest.main()
