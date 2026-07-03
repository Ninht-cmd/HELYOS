"""BusinessScaffolder — « HELYOS crée des business », version crédible et gouvernée.

Ce que ce module FAIT : générer, sous gouvernance, le *squelette* d'un business
(idées produits + copie + pages requises + checklist de lancement). C'est l'application
de l'ADN « transformer le temps en actifs » : faire en une passe ce qui prend des jours.

Ce que ce module NE fait PAS (honnêteté — cf. RFC-0005) : il ne *génère pas d'argent*.
Un scaffold n'est pas un revenu. Les ventes dépendent de la fabrication, du paiement,
du trafic, du marché et du capital — hors périmètre. Et rien n'est publié sur le monde
réel sans passer par le PolicyEngine : la génération du plan est A1 (préparation), mais
toute PUBLICATION est une action externe sensible → validation humaine obligatoire.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from ..governance.autonomy import AutonomyLevel
from ..governance.policy import Action, ActionType, Decision
from ..governance.service import GovernanceService
from ..memory.store import MemoryStore
from ..observability.tracing import span
from .base import Agent
from .llm import LLMPort, StubLLM

DISCLAIMER = ("HELYOS scaffolde la structure d'un business, gouvernée et tracée. "
             "Il ne garantit AUCUN revenu : les ventes dépendent de la fabrication, du "
             "paiement, du trafic, du marché et du capital — hors périmètre d'un scaffolder.")

# Modèle print-on-demand (faible risque PI/légal). Type, spécif, prix indicatif (EUR).
_POD_TEMPLATE = [
    ("Affiche", "affiche A4/A3", "29.90"),
    ("Mug", "mug céramique 330 ml", "19.90"),
    ("Coussin", "coussin décoratif", "34.90"),
    ("Toile", "toile tendue (canvas)", "44.90"),
    ("Plaid", "plaid polaire", "49.90"),
]

_REQUIRED_PAGES = ["Mentions légales", "Conditions Générales de Vente (CGV)",
                   "Politique de confidentialité (RGPD)", "Rétractation & remboursement",
                   "Comment ça marche", "À propos"]

# Actions que HELYOS NE peut/doit PAS faire seul (honnêteté : le vrai goulot).
_HUMAN_CHECKLIST = [
    "[HUMAIN] Créer un compte Printful/Printify + connecter les produits (fournit images + fabrication).",
    "[HUMAIN] Activer le paiement (Shopify Payments/Stripe + identité/RIB) pour encaisser.",
    "[GOUVERNÉ A2] Publier la boutique — action externe, validation humaine requise (voir propose_publish).",
    "[HUMAIN] Budget de test pub + trafic (organique d'abord). Sans trafic, 0 vente.",
]


@dataclass(frozen=True)
class ProductIdea:
    title: str
    description: str
    price: str
    product_type: str


@dataclass(frozen=True)
class BusinessPlan:
    name: str
    niche: str
    model: str
    products: list[ProductIdea] = field(default_factory=list)
    required_pages: list[str] = field(default_factory=list)
    human_checklist: list[str] = field(default_factory=list)
    disclaimer: str = DISCLAIMER

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name, "niche": self.niche, "model": self.model,
            "products": [p.__dict__ for p in self.products],
            "required_pages": self.required_pages,
            "human_checklist": self.human_checklist,
            "disclaimer": self.disclaimer,
        }


class BusinessScaffolder(Agent):
    name = "business_scaffolder"
    description = "Génère (gouverné) le squelette d'un business ; publication = validation humaine."
    required_level = AutonomyLevel.A1  # prépare/propose, n'agit pas seul

    def __init__(self, llm: LLMPort | None = None) -> None:
        self.llm = llm or StubLLM(prefix="[scaffold]")

    def propose(self, context: dict[str, Any]) -> Action:
        niche = str(context.get("niche", "boutique"))
        return Action(type=ActionType.ANALYZE, description=f"Scaffolder un business : {niche}",
                      actor=self.name)

    def scaffold(
        self,
        governance: GovernanceService,
        name: str,
        niche: str,
        model: str = "pod",
        granted: AutonomyLevel = AutonomyLevel.A1,
        memory: MemoryStore | None = None,
    ) -> tuple[Any, BusinessPlan | None]:
        """Génère le plan de business (A1). Ne publie rien : produit un artefact."""
        with span("scaffold.generate", **{"helyos.niche": niche}):
            verdict = governance.submit(self.propose({"niche": niche}), granted)
            if verdict.decision is not Decision.ALLOW:
                return verdict, None

            products = []
            for ptype, spec, price in _POD_TEMPLATE:
                desc = self.llm.complete(
                    f"Rédige une description produit courte et vendeuse pour un {spec} "
                    f"personnalisé sur le thème : {niche}."
                )
                products.append(ProductIdea(
                    title=f"{ptype} personnalisé — {niche}",
                    description=desc, price=price, product_type=ptype))

            plan = BusinessPlan(name=name, niche=niche, model=model, products=products,
                                required_pages=list(_REQUIRED_PAGES),
                                human_checklist=list(_HUMAN_CHECKLIST))
            if memory is not None:
                memory.remember(name, plan.to_dict(), namespace="business")
            governance.bus.emit("scaffold.generated", business=name, niche=niche,
                                products=len(products))
            return verdict, plan

    def propose_publish(
        self,
        governance: GovernanceService,
        plan: BusinessPlan,
        target: str,
        granted: AutonomyLevel = AutonomyLevel.A5,
        validated: bool = False,
    ) -> Any:
        """Proposer de PUBLIER le business sur une plateforme réelle.

        Action externe sensible → GR-2 : validation humaine obligatoire, même en A5.
        C'est le cœur honnête : HELYOS crée le scaffold, mais toucher le monde réel est gouverné.
        """
        with span("scaffold.publish", **{"helyos.target": target}):
            action = Action(
                type=ActionType.EXTERNAL_SENSITIVE,
                description=f"Publier « {plan.name} » sur {target}",
                actor=self.name, sensitive=True, validated=validated,
            )
            return governance.submit(action, granted)
