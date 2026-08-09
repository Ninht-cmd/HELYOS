"""HELYOS — Fusion AST ↔ runtime : confronter ce que l'AST croit à ce que l'exécution montre.

Un finding statique « probablement non testé » devient VÉRIFIABLE :
  couverture 0 %  → confirmed   (l'AST avait raison ; preuve runtime forte)
  couverture haute → contradicted (faux positif ; la fiabilité du mapping baisse)

Ça produit des OutcomeRecord AUTOMATIQUES pour certains findings → la fiabilité des
analyseurs se calibre sur des faits d'exécution, pas seulement sur une validation humaine.

Priorité pondérée par la CRITICITÉ architecturale : un fichier à 0 % n'est pas
automatiquement prioritaire — une branche non testée dans la gouvernance l'est bien plus.
"""

from __future__ import annotations

from dataclasses import dataclass, field

# Criticité par couche (le risque de ne pas tester ce code).
CRITICALITY = {"governance": 1.0, "memory": 0.85, "world": 0.8, "kernel": 0.8, "planner": 0.85,
               "agents": 0.6, "business": 0.6, "connectors": 0.6, "integrations": 0.5,
               "api": 0.4, "observability": 0.3, "eval": 0.3, "licensing": 0.4}


@dataclass
class RuntimeCoverageFinding:
    file: str
    symbol: str | None
    lines_total: int
    lines_covered: int
    coverage_pct: float
    branches_total: int | None = None
    branches_covered: int | None = None
    static_prediction: str | None = None
    runtime_verdict: str = "unknown"        # confirmed | contradicted | partial | unknown
    evidence: list = field(default_factory=list)


@dataclass
class CIRun:
    provider: str
    commit_sha: str
    status: str
    conclusion: str
    tests_passed: int | None = None
    tests_failed: int | None = None
    coverage_pct: float | None = None
    source_freshness: float = 1.0


def _norm(p: str) -> str:
    return p.replace("\\", "/")


def _layer(file: str) -> str:
    parts = _norm(file).split("/")
    return parts[parts.index("jarvis_kernel") + 1] if "jarvis_kernel" in parts else ""


def verdict(coverage_pct: float, low: float = 0.05, high: float = 0.70) -> str:
    if coverage_pct <= low:
        return "confirmed"
    if coverage_pct >= high:
        return "contradicted"
    return "partial"


def fuse_untested(ast_findings: list[dict], coverage_map: dict) -> list[RuntimeCoverageFinding]:
    """Confronte chaque finding AST 'untested' à la couverture runtime réelle du fichier."""
    cov_by = {_norm(k): v for k, v in coverage_map.items()}
    out = []
    for f in ast_findings:
        if f.get("category") != "untested":
            continue
        cov = cov_by.get(_norm(f["file"]))
        if cov is None:
            out.append(RuntimeCoverageFinding(f["file"], f.get("symbol"), 0, 0, 0.0,
                       static_prediction="untested", runtime_verdict="unknown",
                       evidence=["module non mesuré par coverage.py"]))
            continue
        pct = cov["coverage_pct"]
        v = verdict(pct)
        ev = [f"couverture runtime {pct * 100:.0f}% ({cov['lines_covered']}/{cov['lines_total']} lignes)",
              "preuve d'exécution réelle (coverage.py)"]
        out.append(RuntimeCoverageFinding(f["file"], f.get("symbol"), cov["lines_total"],
                   cov["lines_covered"], pct, static_prediction="untested", runtime_verdict=v, evidence=ev))
    return out


def priority(file: str, coverage_pct: float, confidence: float) -> float:
    """Priority = Risk × (1 − Coverage) × Confidence. Un utilitaire à 0 % passe APRÈS
    une couche critique partiellement couverte."""
    risk = CRITICALITY.get(_layer(file), 0.5)
    return round(risk * (1 - coverage_pct) * confidence, 4)


def changed_lines_coverage(covered_lines: list[int], changed_lines: list[int]) -> float:
    """Couverture des LIGNES MODIFIÉES (bien plus pertinent que le delta global)."""
    if not changed_lines:
        return 1.0
    covered = set(covered_lines)
    return round(sum(1 for ln in changed_lines if ln in covered) / len(changed_lines), 4)


@dataclass
class CoverageVerdict:
    status: str            # confirmed | contradicted | executed_no_assertion | partial | unknown
    static_claim: str
    runtime_fact: str
    confidence: float
    evidence: list = field(default_factory=list)


class CoverageTruthResolver:
    """AST propose, le runtime tranche. Distingue « exécuté » de « testé avec assertion » :
    coverage.py prouve qu'une ligne s'exécute, pas qu'un comportement est vérifié."""

    def resolve(self, static_finding: dict, coverage_map: dict, *, symbol_asserted: bool = False) -> CoverageVerdict:
        cov_by = {_norm(k): v for k, v in coverage_map.items()}
        claim = f"{static_finding.get('symbol')} : {static_finding.get('category')} (hypothèse AST)"
        cov = cov_by.get(_norm(static_finding.get("file", "")))
        if cov is None:
            return CoverageVerdict("unknown", claim, "module non mesuré", 0.3,
                                   ["coverage.py n'a pas mesuré ce fichier"])
        pct = cov["coverage_pct"]
        critical = CRITICALITY.get(_layer(static_finding.get("file", "")), 0.5) >= 0.8
        if pct <= 0.05:
            ev = ["coverage.py runtime report", "aucune ligne exécutée par la suite"]
            if critical:
                ev.append("code CRITIQUE jamais exécuté (couche sensible)")
            return CoverageVerdict("confirmed", claim, f"{pct * 100:.0f}% exécuté", 0.99, ev)
        if pct >= 0.70:
            ev = ["coverage.py runtime report", f"{pct * 100:.0f}% exécuté : la claim « non exécuté » est fausse"]
            if not symbol_asserted:
                ev.append("nuance : exécuté transitivement mais aucun test ne NOMME le symbole "
                          "(exécution ≠ validation comportementale)")
            return CoverageVerdict("contradicted", claim, f"{pct * 100:.0f}% exécuté", 0.99, ev)
        return CoverageVerdict("partial", claim, f"{pct * 100:.0f}% exécuté", 0.7,
                               ["couverture partielle — vérité runtime incertaine"])


def tested_symbols(root) -> set:
    from .ast_analysis import build_index_from_root
    _idx, tidx = build_index_from_root(root)
    return tidx.all_used()


def verify_coverage(root, memory=None, objective_id: str | None = None) -> dict:
    """Boucle runtime-truth complète : AST génère les hypothèses « untested », coverage.py
    tranche, la mémoire enregistre les verdicts (calibrant la fiabilité de l'analyseur)."""
    from dataclasses import asdict as _asdict
    from .ast_analysis import build_index_from_root, test_coverage_gaps
    from .coverage_runner import measure_coverage
    idx, tidx = build_index_from_root(root)
    untested = [_asdict(f) for f in test_coverage_gaps(idx, tidx)]
    cov = measure_coverage(root)
    tested = tidx.all_used()
    resolver = CoverageTruthResolver()
    verdicts = [resolver.resolve(f, cov, symbol_asserted=(f.get("symbol") in tested)) for f in untested]
    stats = {"confirmed": 0, "contradicted": 0, "partial": 0, "unknown": 0, "executed_no_assertion": 0}
    for f, v in zip(untested, verdicts):
        stats[v.status] = stats.get(v.status, 0) + 1
        if memory is not None and objective_id is not None:
            if v.status == "confirmed":
                d = memory.record_decision(objective_id, "TestCoverageMapper",
                                           f"non exécuté confirmé : {f['symbol']}", status="confirmed",
                                           entities=[str(f["symbol"]), "category:untested"])
                memory.record_outcome(d, observed=1.0, expected=1.0, note="0% runtime")
            elif v.status == "contradicted":
                d = memory.record_decision(objective_id, "TestCoverageMapper",
                                           f"non testé INFIRMÉ : {f['symbol']}", status="proposed",
                                           entities=[str(f["symbol"]), "category:untested"])
                memory.set_decision_status(d, "rejected", v.runtime_fact)
    return {"stats": stats, "verdicts": verdicts}


def record_verifications(memory, objective_id: str, runtime: list[RuntimeCoverageFinding]) -> dict:
    """Transforme les verdicts runtime en OutcomeRecord automatiques → la fiabilité du
    TestCoverageMapper se calibre (confirmé = +1 ; infirmé = faux positif enregistré)."""
    stats = {"confirmed": 0, "contradicted": 0, "partial": 0, "unknown": 0}
    for rf in runtime:
        stats[rf.runtime_verdict] = stats.get(rf.runtime_verdict, 0) + 1
        if rf.runtime_verdict == "confirmed":
            d = memory.record_decision(objective_id, "TestCoverageMapper",
                                       f"non testé confirmé : {rf.symbol}", status="confirmed",
                                       confidence=0.9, entities=[str(rf.symbol), "category:untested"])
            memory.record_outcome(d, observed=1.0, expected=1.0, note="couverture runtime 0 %")
        elif rf.runtime_verdict == "contradicted":
            d = memory.record_decision(objective_id, "TestCoverageMapper",
                                       f"non testé INFIRMÉ (faux positif) : {rf.symbol}", status="proposed",
                                       confidence=0.9, entities=[str(rf.symbol), "category:untested"])
            memory.set_decision_status(d, "rejected", f"couverture runtime {rf.coverage_pct * 100:.0f}%")
    return stats
