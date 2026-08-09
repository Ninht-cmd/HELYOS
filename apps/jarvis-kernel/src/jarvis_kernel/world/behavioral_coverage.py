"""HELYOS — couverture COMPORTEMENTALE des composants sensibles.

Pour la gouvernance / la mémoire / le planner, « 90 % de lignes couvertes » ne suffit
pas : on veut savoir si les BRANCHES CRITIQUES qui portent les garanties sont réellement
exercées. Ces sondes exécutent le vrai code et vérifient un comportement, pas une ligne :

  • EXTERNAL_SENSITIVE non validé  → REQUIRE_VALIDATION (GR-2)
  • DELETE sans sauvegarde         → DENY (GR-1)
  • A5 financier non validé        → REQUIRE_VALIDATION (GR-7 prime sur le niveau)
  • SELF_PERMISSION                → DENY (GR-3)
  • mémoire « rejected »           → le Planner ne repropose pas

Couverture quantitative (coverage.py) + couverture comportementale (ici) = vérité solide.
"""

from __future__ import annotations

from ..governance.autonomy import AutonomyLevel
from ..governance.policy import Action, ActionType, Decision, PolicyEngine


def _probe_external_sensitive() -> bool:
    v = PolicyEngine().evaluate(
        Action(type=ActionType.EXTERNAL_SENSITIVE, actor="probe", sensitive=True), AutonomyLevel.A5)
    return v.decision is Decision.REQUIRE_VALIDATION and v.rule == "GR-2"


def _probe_delete_without_backup() -> bool:
    v = PolicyEngine().evaluate(
        Action(type=ActionType.DELETE, actor="probe", has_backup=False), AutonomyLevel.A5)
    return v.decision is Decision.DENY and v.rule == "GR-1"


def _probe_financial_never_autonomous() -> bool:
    v = PolicyEngine().evaluate(
        Action(type=ActionType.FINANCIAL, actor="probe"), AutonomyLevel.A5)
    return v.decision is Decision.REQUIRE_VALIDATION and v.rule == "GR-7"


def _probe_self_permission_denied() -> bool:
    v = PolicyEngine().evaluate(
        Action(type=ActionType.SELF_PERMISSION, actor="probe"), AutonomyLevel.A5)
    return v.decision is Decision.DENY and v.rule == "GR-3"


def _probe_memory_no_repropose() -> bool:
    from .memory_store import UnifiedMemory
    from .planner import default_orchestrator
    from ..governance.service import GovernanceService
    mem, orch, gov = UnifiedMemory(), default_orchestrator(), GovernanceService()
    cands = {"candidates": ["piste-A", "piste-B"]}
    r1 = orch.run("Analyse HELYOS et propose une amélioration", cands,
                  governance=gov, granted=AutonomyLevel.A2, memory=mem)
    did = next(s for s in r1["etapes"] if s["kind"] == "propose")["decision_id"]
    first = mem.decisions[did].content
    mem.set_decision_status(did, "rejected", "refusé")
    r2 = orch.run("Analyse encore HELYOS", cands, governance=gov, granted=AutonomyLevel.A2, memory=mem)
    did2 = next(s for s in r2["etapes"] if s["kind"] == "propose")["decision_id"]
    return mem.decisions[did2].content != first


# (nom, sonde, criticité, garantie vérifiée)
CRITICAL_BEHAVIORS = [
    ("external_sensitive_requires_validation", _probe_external_sensitive, 1.0, "GR-2"),
    ("delete_without_backup_denied", _probe_delete_without_backup, 1.0, "GR-1"),
    ("financial_never_autonomous", _probe_financial_never_autonomous, 1.0, "GR-7"),
    ("self_permission_denied", _probe_self_permission_denied, 1.0, "GR-3"),
    ("memory_no_repropose", _probe_memory_no_repropose, 0.85, "mémoire→plan"),
]


def run_behavioral_coverage() -> dict:
    """Exécute chaque sonde de comportement critique. Renvoie le détail + le taux couvert."""
    results = []
    for name, probe, crit, guarantee in CRITICAL_BEHAVIORS:
        try:
            ok = bool(probe())
        except Exception as e:                          # pragma: no cover
            ok = False
            guarantee = f"{guarantee} (erreur: {type(e).__name__})"
        results.append({"behavior": name, "guarantee": guarantee, "criticality": crit, "covered": ok})
    covered = sum(1 for r in results if r["covered"])
    return {"total": len(results), "covered": covered,
            "behavioral_coverage_pct": round(covered / len(results), 3) if results else 0.0,
            "results": results}
