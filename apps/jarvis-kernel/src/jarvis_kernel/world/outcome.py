"""HELYOS — Outcome Analyzer : reboucler le résultat réel dans le Planner (brique #1, boucle 2).

« HELYOS se souvient » → « HELYOS compare prévu ↔ réel, comprend l'écart, adapte le plan ».

Le Planner ne reçoit pas 50 événements bruts : il reçoit des `OutcomeInsight` synthétiques.
Ratio de réussite R = observé / attendu ; catégories (seuils CONFIGURABLES par domaine :
un enjeu médical/financier n'a pas les tolérances d'un enjeu logistique).

Deuxième boucle : `agent_scorecard` — quel agent est fiable pour quel type de problème
(métacognition : « sur 14 décisions similaires, 11 ont produit le résultat attendu »).
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass

# seuils par défaut (à surcharger selon le domaine)
DEFAULT_THRESHOLDS = {"success": 0.95, "partial": 0.50, "weak": 0.0}


def classify(ratio: float | None, thresholds: dict | None = None) -> str:
    th = thresholds or DEFAULT_THRESHOLDS
    if ratio is None:
        return "indetermine"
    if ratio >= th["success"]:
        return "success"
    if ratio >= th["partial"]:
        return "partial_success"
    if ratio > th["weak"]:
        return "weak_success"
    return "failure"


@dataclass
class OutcomeInsight:
    objective_id: str
    expected_value: float | None
    observed_value: float | None
    delta: float | None
    success_ratio: float | None
    decision_id: str | None
    status: str
    lesson: str
    confidence: float
    reusable: bool


class OutcomeAnalyzer:
    def __init__(self, thresholds: dict | None = None) -> None:
        self.th = thresholds or DEFAULT_THRESHOLDS

    def insights(self, memory, objective: str) -> list[OutcomeInsight]:
        recall = memory.retrieve(objective)
        ids = {s["objective_id"] for s in recall["similar_objectives"]}
        out = []
        for d in memory.decisions.values():
            if d.objective_id not in ids or not d.outcome_id:
                continue
            o = memory.outcomes[d.outcome_id]
            R = (o.observed / o.expected) if o.expected else None
            st = classify(R, self.th)
            lesson = (f"La décision « {d.content} » a produit "
                      f"{R * 100:.1f}% de l'effet attendu ({o.observed} vs {o.expected})."
                      if R is not None else f"Résultat indéterminé pour « {d.content} ».")
            out.append(OutcomeInsight(
                objective_id=d.objective_id, expected_value=o.expected, observed_value=o.observed,
                delta=round(o.observed - o.expected, 2) if o.expected is not None else None,
                success_ratio=round(R, 4) if R is not None else None, decision_id=d.id, status=st,
                lesson=lesson, confidence=round(d.confidence or 0.9, 2),
                reusable=st in ("success", "partial_success")))
        out.sort(key=lambda i: (i.success_ratio or 0), reverse=True)
        return out

    def render(self, memory, insights: list[OutcomeInsight]) -> str:
        if not insights:
            return ""
        i = insights[0]
        ep = memory.episodes.get(i.objective_id)
        ratio = f"{i.success_ratio * 100:.1f}%" if i.success_ratio is not None else "?"
        gap = abs(i.delta) if i.delta is not None else "?"
        return (f"Objectif précédent : {ep.objective if ep else i.objective_id}. "
                f"Décision : {memory.decisions[i.decision_id].content}. "
                f"Attendu : {i.expected_value} ; Observé : {i.observed_value} ; "
                f"Écart restant : {gap} points ; Ratio : {ratio} ; "
                f"État : {i.status} ; Confiance : {i.confidence}.")

    # ---- boucle 2 : performance des agents (métacognition) ----
    def agent_scorecard(self, memory) -> dict:
        agg = defaultdict(lambda: {"decisions": 0, "confirmed": 0, "ratios": []})
        for d in memory.decisions.values():
            a = agg[d.agent]
            a["decisions"] += 1
            if d.outcome_id:
                o = memory.outcomes[d.outcome_id]
                R = (o.observed / o.expected) if o.expected else None
                if R is not None:
                    a["ratios"].append(R)
                    if classify(R, self.th) in ("success", "partial_success"):
                        a["confirmed"] += 1
        cards = {}
        for agent, v in agg.items():
            n = len(v["ratios"])
            cards[agent] = {"decisions": v["decisions"], "avec_resultat": n, "confirmes": v["confirmed"],
                            "ratio_moyen": round(sum(v["ratios"]) / n, 3) if n else None,
                            "confiance_calibree": round(v["confirmed"] / n, 3) if n else None}
        return cards
