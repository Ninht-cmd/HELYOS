"""HELYOS — Diff coverage : « la CI est verte » → « les lignes de CETTE décision sont
réellement exercées et suffisamment validées ».

Une couverture GLOBALE de 91 % peut masquer une couverture de DIFF de 42 % : pour une
modification issue d'une décision HELYOS, seule la seconde compte. On rattache le diff à la
décision qui l'a causé et on reconstruit la chaîne de preuve :

    Décision → Patch → Commit → Lignes modifiées → Couverture runtime → CI → Outcome

Cinq niveaux distincts (une agrégation ne doit jamais cacher un trou critique) :
    global_coverage · module_coverage · diff_coverage · critical_diff_coverage
    · behavioral_diff_validation

Verdict rattaché à la décision :
    CHANGE_BROKEN                      — la CI casse (régression).
    CHANGE_NOT_SUFFICIENTLY_VALIDATED — CI verte mais nouvelles lignes/branches critiques
                                        insuffisamment exercées → PAS de crédit de calibration.
    CHANGE_CONFIRMED                  — CI verte ET diff couvert ET chemin critique exercé
                                        ET sonde comportementale OK → crédit de calibration.

Le point clé pédagogique : « vert » ne vaut pas « prouvé ». Un agent qui n'a fait que ne
pas casser la suite existante ne mérite pas encore d'être crédité.
"""

from __future__ import annotations

import re
import subprocess
from dataclasses import dataclass, field
from pathlib import Path

from .confidence import analyzer_reliability, change_assurance

CHANGE_BROKEN = "CHANGE_BROKEN"
CHANGE_NOT_SUFFICIENTLY_VALIDATED = "CHANGE_NOT_SUFFICIENTLY_VALIDATED"
CHANGE_CONFIRMED = "CHANGE_CONFIRMED"

# Seuils (documentés, ajustables) pour promouvoir une modification en CHANGE_CONFIRMED.
DIFF_COVERAGE_FLOOR = 0.90          # ≥ 90 % des lignes modifiées exécutables exercées
CRITICAL_COVERAGE_FLOOR = 1.0       # 100 % des lignes critiques modifiées exercées
ASSURANCE_FLOOR = 0.50             # assurance composite minimale

# Marqueurs d'une ligne « critique » : elle porte une garantie de gouvernance.
CRITICAL_MARKERS = re.compile(
    r"GR-\d|REQUIRE_VALIDATION|Decision\.DENY|EXTERNAL_SENSITIVE|SELF_PERMISSION|"
    r"has_backup|sensitive|FINANCIAL|require_validation|\bDENY\b")

# Couches architecturales critiques (une ligne n'est « critique » que dans ces couches).
CRITICAL_LAYERS = {"governance", "memory", "planner", "kernel"}


@dataclass
class DiffCoverageFinding:
    """Preuve causale : ce diff (issu de cette décision) est-il suffisamment prouvé ?"""
    file: str
    decision_id: str = ""
    base_sha: str = ""
    head_sha: str = ""
    changed_executable_lines: int = 0
    covered_changed_lines: int = 0
    diff_coverage_pct: float = 0.0
    critical_lines: list = field(default_factory=list)
    critical_lines_covered: list = field(default_factory=list)
    ci_status: str = "success"
    behavioral_ok: bool = True
    change_assurance: float = 0.0
    verdict: str = CHANGE_NOT_SUFFICIENTLY_VALIDATED
    evidence: list = field(default_factory=list)

    @property
    def critical_path_coverage(self) -> float:
        return round(len(self.critical_lines_covered) / len(self.critical_lines), 4) \
            if self.critical_lines else 1.0


@dataclass
class DiffReport:
    base_sha: str
    head_sha: str
    decision_id: str
    findings: list
    global_coverage: float
    module_coverage: float
    diff_coverage: float
    critical_diff_coverage: float
    behavioral_diff_validation: bool
    change_assurance: float
    verdict: str

    def levels(self) -> dict:
        return {"global_coverage": self.global_coverage, "module_coverage": self.module_coverage,
                "diff_coverage": self.diff_coverage, "critical_diff_coverage": self.critical_diff_coverage,
                "behavioral_diff_validation": self.behavioral_diff_validation}


def _norm(p: str) -> str:
    return p.replace("\\", "/")


def _is_source(path: str) -> bool:
    p = _norm(path)
    return p.endswith(".py") and "/tests/" not in p and not Path(p).name.startswith("test_")


def _layer(path: str) -> str:
    parts = _norm(path).split("/")
    if "jarvis_kernel" in parts:
        i = parts.index("jarvis_kernel")
        if i + 1 < len(parts):
            return parts[i + 1]
    for seg in parts:                           # sinon : premier segment reconnu comme une couche
        if seg in CRITICAL_LAYERS:
            return seg
    return parts[0] if parts else ""


def parse_diff_added_lines(patch: str) -> dict:
    """Extrait, par fichier, l'ensemble des numéros de lignes AJOUTÉES/MODIFIÉES côté HEAD.
    Robuste au format unifié (avec ou sans contexte)."""
    added: dict[str, set] = {}
    cur: str | None = None
    newln = 0
    for line in patch.splitlines():
        if line.startswith("+++ "):
            p = line[4:].strip()
            if p.startswith("b/"):
                p = p[2:]
            cur = None if p == "/dev/null" else p
            if cur:
                added.setdefault(cur, set())
        elif line.startswith("@@"):
            m = re.search(r"\+(\d+)(?:,(\d+))?", line)
            newln = int(m.group(1)) if m else 0
        elif cur is not None:
            if line.startswith("+") and not line.startswith("+++"):
                added.setdefault(cur, set()).add(newln)
                newln += 1
            elif line.startswith("-") and not line.startswith("---"):
                pass                            # ligne supprimée : le compteur HEAD n'avance pas
            elif line.startswith(" ") or not line:
                newln += 1
    return added


def git_diff(root, base: str, head: str) -> str:
    try:
        r = subprocess.run(["git", "diff", "--unified=0", f"{base}..{head}"],
                           cwd=str(root), capture_output=True, text=True,
                           encoding="utf-8", errors="replace", timeout=15)
        return (r.stdout or "") if r.returncode == 0 else ""
    except Exception:
        return ""


def _critical_added_lines(root, file: str, added: set) -> set:
    """Parmi les lignes ajoutées, celles qui portent une garantie de gouvernance."""
    if _layer(file) not in CRITICAL_LAYERS:
        return set()
    try:
        text = (Path(root) / file).read_text(encoding="utf-8").splitlines()
    except Exception:
        return set()
    crit = set()
    for ln in added:
        if 1 <= ln <= len(text) and CRITICAL_MARKERS.search(text[ln - 1]):
            crit.add(ln)
    return crit


class DiffCoverageAnalyzer:
    """Confronte les lignes d'un diff à la couverture runtime réelle (coverage.py), par
    fichier, en distinguant lignes ordinaires et lignes critiques de gouvernance."""

    def analyze(self, base_sha: str, head_sha: str, patch: str, coverage_map: dict, *,
                root=".", decision_id: str = "", ci_status: str = "success",
                behavioral_ok: bool = True, analyzer_reliability_score: float = 0.6) -> DiffReport:
        cov_by = {_norm(k): v for k, v in coverage_map.items()}
        added = parse_diff_added_lines(patch)
        findings: list[DiffCoverageFinding] = []
        tot_exec = tot_cov = crit_tot = crit_cov = 0

        for file, add_lines in added.items():
            if not _is_source(file):
                continue
            cov = cov_by.get(_norm(file))
            if cov is None:                     # fichier hors instrumentation : non mesuré (honnête)
                findings.append(DiffCoverageFinding(
                    file=file, decision_id=decision_id, base_sha=base_sha, head_sha=head_sha,
                    ci_status=ci_status, evidence=["fichier non mesuré par coverage.py"]))
                continue
            executable = set(cov.get("executable_lines", []))
            covered = set(cov.get("covered_lines", []))
            changed_exec = sorted(add_lines & executable)
            changed_cov = sorted(set(changed_exec) & covered)
            crit = _critical_added_lines(root, file, set(changed_exec))
            crit_covered = sorted(crit & covered)
            pct = round(len(changed_cov) / len(changed_exec), 4) if changed_exec else 1.0
            f = DiffCoverageFinding(
                file=file, decision_id=decision_id, base_sha=base_sha, head_sha=head_sha,
                changed_executable_lines=len(changed_exec), covered_changed_lines=len(changed_cov),
                diff_coverage_pct=round(pct * 100, 1), critical_lines=sorted(crit),
                critical_lines_covered=crit_covered, ci_status=ci_status, behavioral_ok=behavioral_ok,
                evidence=[f"{len(changed_cov)}/{len(changed_exec)} lignes modifiées exécutées",
                          f"{len(crit_covered)}/{len(crit)} lignes critiques exercées"])
            findings.append(f)
            tot_exec += len(changed_exec)
            tot_cov += len(changed_cov)
            crit_tot += len(crit)
            crit_cov += len(crit_covered)

        diff_cov = round(tot_cov / tot_exec, 4) if tot_exec else 1.0
        crit_diff_cov = round(crit_cov / crit_tot, 4) if crit_tot else 1.0
        global_cov = _aggregate(cov_by.values())
        touched = [cov_by[_norm(f.file)] for f in findings if _norm(f.file) in cov_by]
        module_cov = _aggregate(touched)
        assurance = change_assurance(ci_status == "success", diff_cov, crit_diff_cov,
                                     behavioral_ok, analyzer_reliability_score)
        verdict = _decide(ci_status, diff_cov, crit_diff_cov, behavioral_ok, assurance)

        # verdict par finding (chaîne de preuve individuelle)
        for f in findings:
            f.change_assurance = change_assurance(ci_status == "success", f.diff_coverage_pct / 100,
                                                  f.critical_path_coverage, behavioral_ok,
                                                  analyzer_reliability_score)
            f.verdict = _decide(ci_status, f.diff_coverage_pct / 100, f.critical_path_coverage,
                                behavioral_ok, f.change_assurance)

        return DiffReport(base_sha, head_sha, decision_id, findings, global_cov, module_cov,
                          diff_cov, crit_diff_cov, behavioral_ok, assurance, verdict)


def _aggregate(covs) -> float:
    covs = list(covs)
    tot = sum(c.get("lines_total", 0) for c in covs)
    cov = sum(c.get("lines_covered", 0) for c in covs)
    return round(cov / tot, 4) if tot else 1.0


def _decide(ci_status: str, diff_cov: float, crit_cov: float, behavioral_ok: bool,
            assurance: float) -> str:
    if ci_status != "success":
        return CHANGE_BROKEN
    if (diff_cov >= DIFF_COVERAGE_FLOOR and crit_cov >= CRITICAL_COVERAGE_FLOOR
            and behavioral_ok and assurance >= ASSURANCE_FLOOR):
        return CHANGE_CONFIRMED
    return CHANGE_NOT_SUFFICIENTLY_VALIDATED


def diff_coverage_report(root, base: str, head: str, coverage_map: dict, *, decision_id: str = "",
                         ci_status: str = "success", behavioral_ok: bool = True, memory=None) -> DiffReport:
    """Point d'entrée haut niveau : diffe base..head, mesure la couverture des lignes
    modifiées, calibre la fiabilité de l'analyseur via la mémoire."""
    patch = git_diff(root, base, head)
    rel = analyzer_reliability(memory, "diff_coverage")[0] if memory is not None else 0.6
    return DiffCoverageAnalyzer().analyze(base, head, patch, coverage_map, root=root,
                                          decision_id=decision_id, ci_status=ci_status,
                                          behavioral_ok=behavioral_ok, analyzer_reliability_score=rel)


def record_change_outcome(memory, decision_id: str, report: DiffReport) -> str:
    """Traduit le verdict de diff coverage en apprentissage mémoire — le point CRUCIAL :

      • CHANGE_CONFIRMED               → décision confirmée + outcome (crédit de calibration).
      • CHANGE_NOT_SUFFICIENTLY_VALIDATED → NEUTRE : aucun crédit malgré la CI verte
                                          (« vert » ≠ « prouvé ») ; on journalise pourquoi.
      • CHANGE_BROKEN                  → décision rejetée (la CI a cassé).

    Renvoie le statut appliqué à la décision."""
    if decision_id not in memory.decisions:
        return "unknown"
    ev = {"verdict": report.verdict, "diff_coverage": report.diff_coverage,
          "critical_diff_coverage": report.critical_diff_coverage,
          "change_assurance": report.change_assurance, "ci_status": report.findings and
          report.findings[0].ci_status or "success"}
    if report.verdict == CHANGE_CONFIRMED:
        memory.set_decision_status(decision_id, "confirmed",
                                   f"diff coverage {report.diff_coverage * 100:.0f}% · "
                                   f"chemin critique {report.critical_diff_coverage * 100:.0f}%")
        memory.record_outcome(decision_id, observed=report.change_assurance, expected=1.0,
                              note="modification suffisamment prouvée", assurance=ev)
        return "confirmed"
    if report.verdict == CHANGE_BROKEN:
        memory.set_decision_status(decision_id, "rejected", "la CI casse après ce diff")
        return "rejected"
    # NEUTRE : on n'accorde aucun crédit. Journalisé comme événement, pas comme outcome positif.
    memory.record_event("outcome", memory.decisions[decision_id].objective_id, "diff_coverage",
                        f"changement insuffisamment validé : diff {report.diff_coverage * 100:.0f}%, "
                        f"chemin critique {report.critical_diff_coverage * 100:.0f}%",
                        status="proposed", entities=memory.decisions[decision_id].entities)
    return "insufficient"
