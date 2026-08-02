"""Exécute le Supply Chain OS de bout en bout et exporte les VRAIES sorties du moteur
en JSON (utilisé pour alimenter le visuel `supply_chain_run.html`).

    python scripts/render_supply_chain_run.py [chemin_sortie.json]

Reproductible (graines fixes). Aucune donnée inventée : tout vient du moteur.
"""

from __future__ import annotations

import json
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "apps" / "jarvis-kernel" / "src"))

from jarvis_kernel.world.ontology import KnowledgeGraph                       # noqa: E402
from jarvis_kernel.world.domains import full_ontology                        # noqa: E402
from jarvis_kernel.world.domains.supply_chain import (inventory_policy,       # noqa: E402
    service_level_distribution, capacity_utilization)
from jarvis_kernel.world.learning import CausalLaw, calibration, close_loop  # noqa: E402
from jarvis_kernel.world.registry import ModelRegistry                       # noqa: E402

NOW = 1_000_000.0
P = dict(demand=10, sigma_demand=2, lead_time=9, sigma_lead_time=1, service_level=0.95,
         annual_demand=3650, order_cost=50, holding_cost=2, stockout_cost=20)


def run() -> dict:
    g = KnowledgeGraph(full_ontology())
    g.add_entity("Supplier", "FRN-07", "Fournisseur Moteurs SA", now=NOW,
                 values={"lead_time_mean": 9, "lead_time_std": 1, "reliability": 0.94, "unit_price": 180},
                 meta={"pays": "Allemagne"})
    g.add_entity("Stock", "SKU-COQUE", "Coque robot X", now=NOW,
                 values={"demand_mean": 10, "demand_std": 2, "on_hand": 140,
                         "holding_cost": 2, "order_cost": 50, "stockout_cost": 20})
    g.add_entity("Capacity", "CNC-1", "Centre CNC", now=NOW, values={"capacite": 12})
    entities = [{"id": e.id, "type": e.type, "label": e.label, "meta": e.meta,
                 "attrs": {a: round(g.value(e.id, a), 3) for a in g.onto.entity_type(e.type).attrs
                           if g.attr(e.id, a) is not None}} for e in g.entities.values()]

    pol = inventory_policy(**P)
    mc_before = service_level_distribution(P["demand"] * P["lead_time"], pol["sigma_dlt"],
                                           pol["reorder_point"], n=20000, seed=1, bins=26)

    rng = random.Random(7)
    law = CausalLaw("lead_time", "FRN-07.one", "FRN-07.lead_time", 9.0, 3.0, 1.5)
    traj = close_loop(law, [(1.0, rng.gauss(14.0, 1.5)) for _ in range(60)])
    learning = {"start": 9.0, "truth": 14.0, "final_coef": round(law.coef_mean, 3),
                "final_sigma": round(law.coef_sigma, 4),
                "trajectory": [{"pas": t["pas"], "coef": t["coef"], "sigma": t["coef_sigma"]} for t in traj]}

    val = [(1.0, rng.gauss(14.0, 1.5)) for _ in range(120)]
    reg = ModelRegistry()
    champ = CausalLaw("lead_time", "FRN-07.one", "FRN-07.lead_time", 9.0, 3.0, 1.5)
    reg.register(champ, note="a priori 9 j", metrics=calibration(champ, val))
    dec = reg.propose(law, val, note="calibré sur 60 réceptions")
    gov = {"decision": dec["decision"], "champion_rmse": dec["champion"]["rmse"],
           "challenger_rmse": dec["challenger"]["rmse"],
           "versions": [{"version": v.version, "coef": round(v.coef_mean, 3), "sigma": round(v.coef_sigma, 4),
                         "rmse": v.metrics.get("rmse"), "active": reg.active.get("lead_time") == v.version,
                         "note": v.note} for v in reg.history("lead_time")],
           "audit": [{"action": a.action, "version": a.version, "reason": a.reason} for a in reg.audit]}

    lt2 = round(law.coef_mean, 2)
    pol2 = inventory_policy(**{**P, "lead_time": lt2})
    mc_after = service_level_distribution(P["demand"] * lt2, pol2["sigma_dlt"], pol2["reorder_point"],
                                          n=20000, seed=2, bins=26)
    return {"params": P, "entities": entities, "policy_before": pol,
            "capacity_util": round(capacity_utilization(P["demand"], 12), 3),
            "mc_before": mc_before, "event": {"from": 9, "to": 14}, "learning": learning,
            "governance": gov, "lead_time_after": lt2, "policy_after": pol2, "mc_after": mc_after}


if __name__ == "__main__":
    data = run()
    out = sys.argv[1] if len(sys.argv) > 1 else "-"
    if out == "-":
        print(json.dumps(data, ensure_ascii=False, indent=2))
    else:
        Path(out).write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
        print(f"écrit : {out}  (ROP {data['policy_before']['reorder_point']} -> "
              f"{data['policy_after']['reorder_point']} ; gouvernance {data['governance']['decision']})")
