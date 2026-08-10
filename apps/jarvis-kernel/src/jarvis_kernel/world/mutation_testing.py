"""HELYOS — Mutation testing CIBLÉ : les tests SAVENT-ILS détecter une ligne fausse ?

La couverture de diff prouve qu'une ligne critique s'EXÉCUTE. Elle ne prouve pas que les
tests la VÉRIFIENT : un test peut exécuter la ligne GR-2 sans jamais asserter son résultat.
La mutation comble ce trou — mais sous une règle stricte : on ne mute pas « pour un score »,
on mute pour éprouver une PROPRIÉTÉ critique précise.

    diff critique détecté → ligne/propriété ciblée → mutants contrôlés → tests CIBLÉS
       → mutant tué ?  ── oui → preuve forte
                        └─ non → SURVIVANT : produire des HYPOTHÈSES, jamais « bug confirmé »

Sur un survivant, HELYOS ne conclut pas à un bug : il liste les causes possibles (test
insuffisant · mutation équivalente · branche inatteignable · propriété non couverte) et
demande un diagnostic. Un mutant critique survivant NON EXPLIQUÉ empêche CHANGE_CONFIRMED.

Sûreté : chaque mutant est écrit dans le fichier puis RESTAURÉ dans un `finally` (octets
d'origine relus et vérifiés). Prévu pour un arbre jetable ; sur le vrai dépôt, l'appelant
assume la fenêtre de mutation.
"""

from __future__ import annotations

import os
import re
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path

from .diff_coverage import (CHANGE_BROKEN, CHANGE_CONFIRMED, CHANGE_NOT_SUFFICIENTLY_VALIDATED,
                            CRITICAL_MARKERS)

KILLED = "KILLED"
SURVIVED = "SURVIVED"

SURVIVOR_HYPOTHESES = [
    "test insuffisant : la ligne est exécutée mais sa propriété n'est pas assertée",
    "mutation potentiellement équivalente (même comportement observable)",
    "branche jamais atteinte par les tests ciblés",
    "propriété non couverte par une assertion",
]


@dataclass
class MutationFinding:
    target: str                     # fichier:ligne
    mutation_operator: str
    original: str
    mutated: str
    tests_run: list
    result: str                     # KILLED | SURVIVED
    criticality: float
    evidence: list = field(default_factory=list)
    decision_id: str = ""
    confidence: float = 0.0
    hypotheses: list = field(default_factory=list)


@dataclass
class MutationReport:
    findings: list
    decision_id: str = ""

    @property
    def killed(self) -> list:
        return [f for f in self.findings if f.result == KILLED]

    @property
    def survivors(self) -> list:
        return [f for f in self.findings if f.result == SURVIVED]

    @property
    def critical_survivors(self) -> list:
        return [f for f in self.survivors if f.criticality >= 0.8]

    @property
    def mutation_score(self) -> float:
        return round(len(self.killed) / len(self.findings), 4) if self.findings else 1.0

    @property
    def confirmed_ok(self) -> bool:
        """Aucun mutant CRITIQUE survivant inexpliqué → la propriété est protégée."""
        return not self.critical_survivors


def _split_comment(line: str) -> tuple:
    """Sépare le CODE d'un éventuel commentaire de fin (en respectant les chaînes). On ne mute
    jamais un token de commentaire : ce serait une mutation ÉQUIVALENTE (survivant garanti)."""
    quote = None
    for i, ch in enumerate(line):
        if quote:
            if ch == quote:
                quote = None
        elif ch in "\"'":
            quote = ch
        elif ch == "#":
            return line[:i], line[i:]
    return line, ""


def generate_mutants(line: str) -> list:
    """Mutations SÉMANTIQUES simples et dangereuses ciblant une propriété de gouvernance.
    Renvoie [(operateur, ligne_mutée)] pour chaque opérateur applicable à cette ligne."""
    muts = []
    code, comment = _split_comment(line)

    def sub(pattern, repl, name):
        new_code = re.sub(pattern, repl, code, count=1)
        if new_code != code:
            mutated = new_code + comment
            if mutated not in [m[1] for m in muts]:
                muts.append((name, mutated))

    # valeurs de décision dangereuses
    sub(r"\bREQUIRE_VALIDATION\b", "ALLOW", "require_validation_to_allow")
    sub(r'"require_validation"', '"allow"', "require_validation_to_allow")
    sub(r"\bDENY\b", "ALLOW", "deny_to_allow")
    # drapeaux contextuels
    sub(r"\bsensitive\s*=\s*True\b", "sensitive=False", "sensitive_true_to_false")
    sub(r"\bvalidated\s*=\s*False\b", "validated=True", "validated_false_to_true")
    sub(r"\bhas_backup\s*=\s*False\b", "has_backup=True", "has_backup_false_to_true")
    # inversion de condition : if/elif COND: → if/elif not (COND):
    m = re.match(r"^(\s*)(if|elif)\s+(.*?):\s*(#.*)?$", line)
    if m:
        indent, kw, cond, comment = m.groups()
        tail = f"  {comment}" if comment else ""
        muts.append(("negate_condition", f"{indent}{kw} not ({cond}):{tail}"))
    return muts


def critical_targets_in_file(file, criticality: float = 1.0) -> list:
    """Repère les lignes portant un marqueur de gouvernance (mêmes marqueurs que diff_coverage)."""
    try:
        lines = Path(file).read_text(encoding="utf-8").splitlines()
    except Exception:
        return []
    return [(str(file), i, criticality) for i, l in enumerate(lines, 1) if CRITICAL_MARKERS.search(l)]


def _run_targeted_tests(src_dir, tests_dir, pattern: str, timeout: int = 120):
    env = dict(os.environ, PYTHONPATH=str(src_dir), PYTHONIOENCODING="utf-8",
               PYTHONDONTWRITEBYTECODE="1", HELYOS_PULSE_INTERVAL="0")
    p = subprocess.run([sys.executable, "-m", "unittest", "discover", "-s", str(tests_dir), "-p", pattern],
                       capture_output=True, text=True, encoding="utf-8", errors="replace",
                       env=env, cwd=str(src_dir), timeout=timeout)
    return p.returncode == 0, (p.stdout or "") + (p.stderr or "")


def _test_names(output: str) -> list:
    return re.findall(r"^(test_\w+)", output, re.M) or []


def _mutate_and_test(src_dir, tests_dir, file, lineno: int, new_line: str, pattern: str):
    """Écrit le mutant, lance les tests CIBLÉS, RESTAURE toujours (finally + vérification)."""
    path = Path(file)
    original = path.read_bytes()
    try:
        lines = path.read_text(encoding="utf-8").splitlines(keepends=True)
        orig_line = lines[lineno - 1]
        nl = "\n" if orig_line.endswith("\n") else ""
        lines[lineno - 1] = new_line.rstrip("\n") + nl
        path.write_text("".join(lines), encoding="utf-8")
        passed, out = _run_targeted_tests(src_dir, tests_dir, pattern)
    finally:
        path.write_bytes(original)                      # restauration GARANTIE
    if path.read_bytes() != original:                   # garde-fou : l'octet près
        raise RuntimeError(f"restauration du mutant échouée : {file}")
    return (KILLED if not passed else SURVIVED), orig_line.strip(), out


def run_mutation_testing(src_dir, tests_dir, targets, *, pattern: str = "test_*.py",
                         decision_id: str = "") -> MutationReport:
    """Pour chaque ligne critique ciblée, génère des mutants contrôlés et vérifie que les
    tests ciblés les TUENT. Un survivant produit des hypothèses, jamais une conclusion de bug."""
    findings = []
    for file, lineno, crit in targets:
        try:
            line = Path(file).read_text(encoding="utf-8").splitlines()[lineno - 1]
        except Exception:
            continue
        for op_name, mutated in generate_mutants(line):
            result, orig, out = _mutate_and_test(src_dir, tests_dir, file, lineno, mutated, pattern)
            rel = os.path.relpath(file, src_dir).replace("\\", "/")
            findings.append(MutationFinding(
                target=f"{rel}:{lineno}", mutation_operator=op_name, original=orig,
                mutated=mutated.strip(), tests_run=_test_names(out) or [pattern], result=result,
                criticality=crit, decision_id=decision_id,
                evidence=[f"mutant « {op_name} » → tests {'ROUGES (détecté)' if result == KILLED else 'VERTS (non détecté)'}"],
                confidence=0.95 if result == KILLED else 0.4,
                hypotheses=[] if result == KILLED else list(SURVIVOR_HYPOTHESES)))
    return MutationReport(findings, decision_id)


def gated_change_verdict(diff_verdict: str, mutation: MutationReport) -> str:
    """La mutation ne remplace pas les autres preuves : elle ne peut que DÉGRADER un verdict.
    CHANGE_CONFIRMED n'est maintenu que si aucun mutant critique ne survit sans explication."""
    if diff_verdict == CHANGE_BROKEN:
        return CHANGE_BROKEN
    if diff_verdict == CHANGE_CONFIRMED and not mutation.confirmed_ok:
        return CHANGE_NOT_SUFFICIENTLY_VALIDATED
    return diff_verdict


def record_mutation_outcome(memory, decision_id: str, mutation: MutationReport) -> str:
    """Un survivant critique NE confirme PAS et NE rejette PAS : il déclenche un diagnostic
    (neutre pour la calibration). Tous les mutants tués renforcent la confirmation ailleurs."""
    if decision_id not in memory.decisions:
        return "unknown"
    if mutation.critical_survivors:
        memory.record_event("outcome", memory.decisions[decision_id].objective_id, "mutation_testing",
                            f"mutant critique survivant : {mutation.critical_survivors[0].target} "
                            f"({mutation.critical_survivors[0].mutation_operator}) — diagnostic requis",
                            status="proposed", entities=memory.decisions[decision_id].entities)
        return "needs_diagnosis"
    return "clean"
