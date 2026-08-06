"""Supply Chain — la couche AGENT : de « ROP 109 → 159 » à un raisonnement gouverné.

Ferme deux morceaux du fossé avec un vrai agent :
  (A) DONNÉES RÉELLES : `read_receptions_csv` lit un CSV que l'utilisateur remplace par
      ses propres réceptions (pas de données codées en dur).
  (B) COMPORTEMENT D'AGENT : `advise` enchaîne plusieurs étapes — apprendre le délai réel
      de CHAQUE fournisseur, détecter la dérive, identifier un fournisseur alternatif plus
      rapide dans les mêmes données, chiffrer l'impact, PROPOSER des actions, et soumettre
      l'action externe (demande de devis) à la GOUVERNANCE A0–A5 → `REQUIRE_VALIDATION`
      (GR-2). L'agent propose et attend la validation ; il n'envoie jamais seul.

Portée honnête : un seul domaine, un seul type de connecteur (CSV). Le JARVIS
multi-domaines/multi-connecteurs (ERP, Gmail, navigateur…) reste l'ambition large.
"""

from __future__ import annotations

import csv
from pathlib import Path

from ...governance.autonomy import AutonomyLevel
from ...governance.policy import Action, ActionType
from ..learning import CausalLaw
from .supply_chain import inventory_policy


def read_receptions_csv(path: str | Path) -> list[tuple[str, str, float]]:
    """Lit un CSV réel de réceptions -> [(date, fournisseur, délai_jours)]. Colonnes
    attendues : date_reception, fournisseur, delai_jours. À remplacer par tes données."""
    rows = []
    with open(path, newline="", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            try:
                rows.append((r.get("date_reception", ""), r["fournisseur"].strip(),
                             float(r["delai_jours"])))
            except (KeyError, ValueError):
                continue
        return rows


def learn_suppliers(rows: list[tuple[str, str, float]], prior: float = 9.0) -> dict:
    """Apprend le délai réel de chaque fournisseur (régression bayésienne récursive)."""
    groups: dict[str, list[float]] = {}
    for _date, sup, lt in rows:
        groups.setdefault(sup, []).append(lt)
    out = {}
    for sup, lts in groups.items():
        law = CausalLaw(f"lead_time[{sup}]", "sup.one", "sup.lead_time", prior, 3.0, 1.5)
        for lt in lts:
            law.observe(1.0, lt)
        out[sup] = {"learned": round(law.coef_mean, 2), "sigma": round(law.coef_sigma, 3), "n": len(lts)}
    return out


def advise(target: str, rows: list[tuple[str, str, float]], policy_params: dict,
           prior_lead_time: float, governance, granted: AutonomyLevel = AutonomyLevel.A2) -> dict:
    """Produit une recommandation d'agent, gouvernée. Renvoie le récit, l'impact chiffré,
    les alternatives trouvées dans les données, et le verdict de gouvernance sur l'action externe."""
    suppliers = learn_suppliers(rows, prior_lead_time)
    t = suppliers.get(target, {"learned": prior_lead_time, "sigma": 0.0, "n": 0})
    learned = t["learned"]
    drift = round(learned - prior_lead_time, 2)

    # impact chiffré : politique avant / après (mêmes coûts, délai différent)
    pol0 = inventory_policy(**{**policy_params, "lead_time": prior_lead_time})
    pol1 = inventory_policy(**{**policy_params, "lead_time": learned})

    # alternatives réellement présentes dans les données, plus rapides que le fournisseur qui dérive
    alternatives = sorted(
        ({"fournisseur": s, **v} for s, v in suppliers.items() if s != target and v["learned"] < learned),
        key=lambda a: a["learned"])

    # ACTION EXTERNE proposée -> soumise à la gouvernance (GR-2 : validation humaine)
    alt_txt = alternatives[0]["fournisseur"] if alternatives else "(aucune)"
    desc = (f"Envoyer une demande de devis à un fournisseur alternatif ({alt_txt}) "
            f"suite à la dérive de {target} ({prior_lead_time}→{learned} j)")
    verdict = governance.submit(
        Action(type=ActionType.EXTERNAL_SENSITIVE, actor="supply_chain_agent",
               description=desc, sensitive=True), granted)

    recos = [f"Relever le point de commande de {pol0['reorder_point']} à {pol1['reorder_point']} u "
             f"(coût {pol0['total_cost']}→{pol1['total_cost']} €/an)"]
    if alternatives:
        a = alternatives[0]
        recos.append(f"Demander un devis à {a['fournisseur']} (délai appris {a['learned']} j sur {a['n']} réceptions) "
                     f"— action externe, validation requise")

    narrative = (
        f"Le fournisseur {target} dérive : délai {prior_lead_time} → {learned} j "
        f"(appris de {t['n']} réceptions réelles, ±{t['sigma']}). "
        + (f"J'ai identifié un fournisseur alternatif plus rapide dans tes données : "
           f"{alternatives[0]['fournisseur']} (~{alternatives[0]['learned']} j). " if alternatives else "")
        + f"Impact : point de commande {pol0['reorder_point']} → {pol1['reorder_point']} u. "
        f"J'ai préparé la demande de devis ; action externe → {verdict.decision.value} "
        f"({verdict.rule or 'gouvernance'}) : j'attends ta validation avant envoi.")

    return {"target": target, "suppliers": suppliers, "drift_days": drift,
            "learned_lead_time": learned, "rop_before": pol0["reorder_point"],
            "rop_after": pol1["reorder_point"], "cost_before": pol0["total_cost"],
            "cost_after": pol1["total_cost"], "alternatives": alternatives,
            "recommendations": recos,
            "external_action": {"description": desc, "decision": verdict.decision.value,
                                "reason": verdict.reason, "rule": verdict.rule},
            "narrative": narrative}
