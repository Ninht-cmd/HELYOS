"""HELYOS Domain Layer v2.0 — les lobes spécialisés.

Le noyau + l'ontologie donnent un cerveau de COORDINATION. Un vrai conglomérat
industriel exige des DOMAINES : chacun injecte ses entités, ses variables, ses
ÉQUATIONS (les lois causales du domaine), et ses risques.

Chaque domaine est un ``Domain`` : des types d'entités (fusionnés dans l'ontologie
via ``Ontology.extend``) + un dictionnaire d'équations (fonctions pures, testables).
``build_ontology(*domains)`` produit l'ontologie enrichie.

Honnêteté : HELYOS n'est pas SAP + CATIA + Bloomberg. Ces domaines apportent les
LOIS réutilisables (finance, méca, manufacturing) que le Monte-Carlo exploite ;
la profondeur métier de chaque lobe est un chantier continu.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from ..ontology import Ontology, default_ontology


@dataclass
class Domain:
    name: str
    entity_types: dict = field(default_factory=dict)      # {name: EntityType} injectés/enrichis
    relation_types: dict = field(default_factory=dict)
    equations: dict = field(default_factory=dict)         # {nom: fonction pure} — les lois du domaine
    reference_cases: list = field(default_factory=list)   # cas de validation (inputs -> valeur attendue)


def validate_domain(domain: Domain) -> dict:
    """Exécute les cas de référence d'un domaine : chaque équation doit reproduire une
    valeur connue (manuel/norme). C'est la « validation set » au niveau des lois — la
    condition pour faire confiance à un domaine avant de l'alimenter en données réelles."""
    results, ok = [], 0
    for case in domain.reference_cases:
        fn = domain.equations.get(case["equation"])
        try:
            got = fn(**case.get("kwargs", {}))
            passed = abs(got - case["expected"]) <= case.get("tol", 1e-6)
        except Exception as e:                            # pragma: no cover
            got, passed = f"erreur: {e}", False
        ok += bool(passed)
        results.append({"equation": case["equation"], "attendu": case["expected"],
                        "obtenu": round(got, 6) if isinstance(got, float) else got, "ok": bool(passed)})
    return {"domaine": domain.name, "passes": ok, "total": len(domain.reference_cases), "details": results}


def build_ontology(*domains: Domain) -> Ontology:
    """Ontologie de base enrichie par chaque domaine (Domain Schema → Variables)."""
    o = default_ontology()
    for d in domains:
        o.extend(d.entity_types, d.relation_types)
    return o


def all_domains() -> list[Domain]:
    from .finance import FINANCE
    from .engineering import ENGINEERING
    from .trading import TRADING
    return [FINANCE, ENGINEERING, TRADING]


def full_ontology() -> Ontology:
    return build_ontology(*all_domains())
