"""Amorçage du World Model depuis l'état RÉEL d'HELYOS (pas un jouet).

On lit la caisse, la prospection, le portefeuille et les connecteurs, et on en fait
des croyances datées et sourcées. Ce qui est connu exactement (cash, nb de prospects)
a un σ faible ; ce qui est estimé (burn, progrès) a un σ large et une confiance basse
— honnêtement. La fonction d'utilité et la décision travaillent ensuite là-dessus.
"""

from __future__ import annotations

from .decision import Action
from .model import WorldModel


def seed_world(ctx, now: float) -> WorldModel:
    w = WorldModel()

    # --- caisse (connue exactement -> σ faible) ---
    solde = 0.0
    try:
        g = ctx.ledger.global_summary() if getattr(ctx, "ledger", None) else {}
        solde = float(g.get("solde_eur", 0.0) or 0.0)
        w.set("revenu_mensuel", float(g.get("recettes_eur", 0.0) or 0.0), sigma=50.0,
              source="livre de caisse (proxy)", ts=now, unit="€/mois", kind="money")
    except Exception:
        w.set("revenu_mensuel", 0.0, sigma=50.0, source="indisponible", ts=now, unit="€/mois", kind="money")
    w.set("cash", solde, sigma=1.0, source="livre de caisse", ts=now, unit="€", kind="money")

    # --- burn mensuel : INCONNU -> grande incertitude (honnête) ---
    w.set("burn_mensuel", 200.0, sigma=300.0, source="estimé (inconnu)", ts=now, unit="€/mois", kind="money")
    # runway = cash / burn, avec propagation d'incertitude
    w.derive("runway_mois", lambda m: m["cash"] / max(m["burn_mensuel"], 1e-6),
             ["cash", "burn_mensuel"], source="dérivé cash/burn", unit="mois", kind="months")

    # --- prospection / clients (comptages exacts -> σ faible) ---
    try:
        from ..business.prospection import ProspectionPipeline
        s = ProspectionPipeline(ctx.memory).stats()
        w.set("prospects", float(s.get("total", 0)), sigma=0.5, source="pipeline", ts=now, kind="count")
        w.set("clients", float(s.get("clients", 0)), sigma=0.5, source="pipeline", ts=now, kind="count")
    except Exception:
        pass

    # --- connecteurs -> risque opérationnel réel ---
    risk_ops = 0.5
    try:
        cx = ctx.connectors or []
        if cx:
            off = sum(1 for c in cx if c.status().status != "connected")
            risk_ops = off / len(cx)
    except Exception:
        pass
    w.set("risque_ops", risk_ops, sigma=0.1, source="état connecteurs", ts=now, kind="ratio")

    # --- risques structurels connus (on les CONNAÎT -> σ faible) ---
    # pas de canal d'encaissement (Gumroad absent) => risque paiement maximal
    w.set("risque_paiement", 1.0, sigma=0.05, source="aucun canal d'encaissement", ts=now, kind="ratio")
    # micro-entreprise non immatriculée => risque juridique avant 1er euro
    w.set("risque_legal", 1.0, sigma=0.1, source="immatriculation à faire", ts=now, kind="ratio")

    # --- progrès vers l'objectif (estimé -> confiance basse) ---
    progres = 0.10
    try:
        biz = ctx.portfolio.list() if getattr(ctx, "portfolio", None) else []
        if biz:
            active = sum(1 for b in biz if "prêt" in (b.status or "").lower() or "actif" in (b.status or "").lower())
            progres = min(0.6, 0.05 + 0.07 * active)
    except Exception:
        pass
    w.set("progres_objectif", progres, sigma=0.2, source="estimé (statuts business)", ts=now, kind="ratio")

    return w


def default_actions() -> list[Action]:
    """Actions candidates calquées sur les vraies échéances du Pouls. Chaque effet est
    un modèle explicite ; la politique les classera par ΔU."""
    return [
        Action("premier_client", "Décrocher le 1er client (Audit Flash 490 €)", cost=0.02,
               effects=[("clients", "add", 1), ("cash", "add", 490), ("revenu_mensuel", "add", 490),
                        ("progres_objectif", "add", 0.08)]),
        Action("creer_gumroad", "Créer le compte Gumroad (débloque l'encaissement)", cost=0.01,
               effects=[("risque_paiement", "set", 0.0), ("progres_objectif", "add", 0.05)]),
        Action("immatriculation", "Immatriculer la micro-entreprise (URSSAF, gratuit)", cost=0.02,
               effects=[("risque_legal", "set", 0.0), ("progres_objectif", "add", 0.05)]),
        Action("brancher_connecteurs", "Brancher Shopify + SMTP (baisse le risque opérationnel)", cost=0.01,
               effects=[("risque_ops", "mul", 0.3), ("progres_objectif", "add", 0.03)]),
        Action("publier_videos", "Publier 3 vidéos (alimente le haut de tunnel)", cost=0.03,
               effects=[("prospects", "add", 5), ("progres_objectif", "add", 0.02)]),
    ]
