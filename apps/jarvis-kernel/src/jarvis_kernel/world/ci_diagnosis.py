"""HELYOS — Software Incident Intelligence : transformer un FAIL CI en diagnostic.

Chaîne causale reconstruite (pas juste « rouge ») :
  run → job → test → traceback → exception → fichier/symbole → commit fautif probable
  → finding AST/runtime antérieur ? → décision HELYOS liée ? → diagnostic + confiance → GR-2.

Règle clé : ne pas conclure trop vite que le dernier fichier modifié est la cause. Le
diagnostic ACCUMULE plusieurs signaux (traceback, commit, symbole, décision mémoire) et
sa confiance monte avec leur accord. Trois niveaux : observation (le test a-t-il échoué ?),
diagnostic (est-ce cette régression ?), action (le correctif aidera-t-il ?).
"""

from __future__ import annotations

import os
import re
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class CIRun:
    provider: str
    commit_sha: str
    status: str
    conclusion: str
    tests_passed: int | None = None
    tests_failed: int | None = None
    workflow: str = ""
    url: str = ""

    @classmethod
    def from_github(cls, run: dict) -> "CIRun":
        return cls(provider="github_actions", commit_sha=(run.get("head_sha", "") or "")[:7],
                   status=run.get("status", ""), conclusion=run.get("conclusion", ""),
                   workflow=run.get("name", ""), url=run.get("url", run.get("html_url", "")))


@dataclass
class CIFailureFinding:
    test: str
    exception_type: str
    message: str
    file: str | None
    line: int | None = None
    symbol: str | None = None
    workflow: str = ""
    commit_sha: str = ""
    evidence: list = field(default_factory=list)
    culprit_commit: str = ""
    prior_finding: str = ""
    linked_decision: str = ""
    diagnosis: str = ""
    observation_confidence: float = 0.0
    diagnosis_confidence: float = 0.0
    action_confidence: float = 0.0
    recommendation: str = ""


def parse_unittest_failures(output: str) -> list[CIFailureFinding]:
    """Extrait chaque FAIL/ERROR d'une sortie `unittest` : test, exception, et le frame
    de traceback situé dans le CODE SOURCE (pas seulement le fichier de test)."""
    fails = []
    for block in re.split(r"={60,}", output):
        m = re.search(r"^\s*(FAIL|ERROR):\s+(\S+)", block, re.M)
        if not m:
            continue
        test = m.group(2)
        frames = re.findall(r'File "([^"]+)", line (\d+), in (\S+)', block)
        src = [f for f in frames if "jarvis_kernel" in f[0].replace("\\", "/")
               and "tests" not in f[0].replace("\\", "/")]
        frame = (src or frames)[-1] if frames else None
        file = line = symbol = None
        if frame:
            raw = frame[0].replace("\\", "/")
            file = "apps/jarvis-kernel/src/jarvis_kernel/" + raw.split("jarvis_kernel/", 1)[1] \
                if "jarvis_kernel/" in raw else raw
            line, symbol = int(frame[1]), frame[2]
        exc = [l for l in block.splitlines() if re.match(r"^[A-Za-z_][\w.]*(Error|Exception|Failure)?:", l)]
        etype, emsg = (exc[-1].split(":", 1) if exc else ("Failure", ""))
        fails.append(CIFailureFinding(test=test, exception_type=etype.strip(),
                                      message=emsg.strip()[:200], file=file, line=line, symbol=symbol))
    return fails


def run_local_ci(root, tests_dir: str | None = None, pattern: str = "test_*.py") -> tuple[CIRun, list]:
    """Exécute la suite en sous-processus (comme la CI) et renvoie un CIRun + les échecs réels."""
    root = Path(root)
    src = root / "apps" / "jarvis-kernel" / "src"
    tdir = tests_dir or str(root / "apps" / "jarvis-kernel" / "tests")
    env = dict(os.environ, PYTHONPATH=str(src), PYTHONIOENCODING="utf-8", HELYOS_PULSE_INTERVAL="0")
    p = subprocess.run([sys.executable, "-m", "unittest", "discover", "-s", tdir, "-p", pattern],
                       capture_output=True, text=True, env=env, cwd=str(root), timeout=300)
    out = p.stdout + p.stderr
    mtot = re.search(r"Ran (\d+) tests", out)
    mfail = re.search(r"FAILED \(.*?(?:failures=(\d+))?.*?(?:errors=(\d+))?.*?\)", out)
    failed = 0
    if mfail:
        failed = (int(mfail.group(1) or 0) + int(mfail.group(2) or 0))
    total = int(mtot.group(1)) if mtot else 0
    run = CIRun(provider="local", commit_sha=_head_sha(root), status="completed",
                conclusion="success" if p.returncode == 0 else "failure",
                tests_passed=total - failed, tests_failed=failed, workflow="local-unittest")
    return run, parse_unittest_failures(out)


def _git(root, *args) -> str:
    try:
        r = subprocess.run(["git", *args], cwd=str(root), capture_output=True, text=True, timeout=8)
        return r.stdout.strip() if r.returncode == 0 else ""
    except Exception:
        return ""


def _head_sha(root) -> str:
    return _git(root, "rev-parse", "--short", "HEAD")


def git_last_commit_for(root, file: str) -> tuple[str, str]:
    out = _git(root, "log", "-1", "--format=%h|%s", "--", file)
    return tuple(out.split("|", 1)) if "|" in out else ("", "")


def diagnose(failure: CIFailureFinding, root, memory=None) -> CIFailureFinding:
    """Accumule les signaux et produit un diagnostic gouverné (jamais l'écriture auto)."""
    ev = [f"test échoué : {failure.test}", f"exception : {failure.exception_type}: {failure.message}"]
    signals = 1                                        # l'échec lui-même
    if failure.file:
        ev.append(f"frame source : {failure.file}:{failure.line} dans {failure.symbol}")
        signals += 1
        sha, subj = git_last_commit_for(root, failure.file)
        if sha:
            failure.culprit_commit = sha
            ev.append(f"commit récent sur ce fichier : {sha} « {subj[:50]} »")
            signals += 1
    # décision HELYOS antérieure touchant le fichier/symbole ?
    if memory is not None and failure.symbol:
        for d in memory.decisions.values():
            if failure.symbol in d.entities or (failure.file and failure.file in " ".join(d.entities)):
                failure.linked_decision = d.id
                ev.append(f"décision HELYOS liée : {d.id} « {d.content[:50]} »")
                signals += 1
                break

    failure.evidence = ev
    loc = f"{failure.symbol} ({failure.file})" if failure.file else failure.test
    failure.diagnosis = (f"Régression probable dans {loc}"
                         + (f", introduite par {failure.culprit_commit}" if failure.culprit_commit else "")
                         + (f" — liée à la décision {failure.linked_decision}" if failure.linked_decision else "")
                         + ".")
    failure.recommendation = (f"Corriger {loc} et ajouter un test de non-régression pour « {failure.test} ».")
    # trois niveaux de confiance
    failure.observation_confidence = 0.99              # le test a réellement échoué (fait)
    failure.diagnosis_confidence = round(min(0.95, 0.55 + 0.12 * (signals - 1)), 4)  # monte avec l'accord des signaux
    failure.action_confidence = round(failure.diagnosis_confidence * 0.8, 4)         # la correction reste discutable
    return failure


def record_ci_outcome(memory, objective_id: str, ci_passed: bool, related_decisions: list[str]) -> None:
    """Auto-contradiction : si la CI casse alors qu'une décision était « faible risque »,
    l'outcome redescend dans la mémoire → le scorecard du dev_agent baisse."""
    for did in related_decisions:
        if did in memory.decisions:
            if ci_passed:
                memory.record_outcome(did, observed=1.0, expected=1.0, note="CI verte après correction")
            else:
                memory.set_decision_status(did, "rejected", "CI cassée juste après cette décision")
