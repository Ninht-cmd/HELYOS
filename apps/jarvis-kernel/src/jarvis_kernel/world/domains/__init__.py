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


def build_ontology(*domains: Domain) -> Ontology:
    """Ontologie de base enrichie par chaque domaine (Domain Schema → Variables)."""
    o = default_ontology()
    for d in domains:
        o.extend(d.entity_types, d.relation_types)
    return o


def all_domains() -> list[Domain]:
    from .finance import FINANCE
    from .engineering import ENGINEERING
    return [FINANCE, ENGINEERING]


def full_ontology() -> Ontology:
    return build_ontology(*all_domains())
