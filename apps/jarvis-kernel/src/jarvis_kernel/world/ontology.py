"""HELYOS Ontology — le graphe de connaissances typé qui donne un MONDE au noyau.

Le noyau décide (world/decision) ; l'ontologie lui donne de quoi décider : des
*entités* (entreprises, produits, fournisseurs, marchés, actifs, machines, gens…),
leurs *attributs* (typés), et leurs *relations* (fourni_par, produit, impacte,
dépend_de…). C'est le « corps et les organes » autour du cerveau.

Choix d'ingénierie — réutiliser la colonne vertébrale probabiliste, ne pas la
dupliquer :
  • chaque attribut NUMÉRIQUE d'une entité EST une croyance du WorldModel, clé
    ``"<entity_id>.<attr>"`` — donc μ±σ, confiance, fusion bayésienne gratuits ;
  • les attributs textuels/catégoriels vivent dans ``Entity.meta`` (le spine reste numérique) ;
  • une relation est une arête typée ; une entité peut avoir des attributs DÉRIVÉS
    d'attributs d'autres entités atteintes par une relation — d'où la SIMULATION :
    ``simulate()`` change des attributs et re-dérive la chaîne, l'incertitude se
    propageant (jacobienne numérique de WorldModel.derive). Multi-sauts, chiffré.

L'ontologie elle-même (types d'entités, d'attributs, de relations) est de la DONNÉE
(``default_ontology()`` / JSON) : ajouter un domaine = éditer le schéma, pas le code.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable

from .model import WorldModel

# natures d'attribut -> soit croyance numérique (kind du WorldModel), soit méta (texte/catégoriel)
_NUMERIC = {"money", "count", "ratio", "months", "metric"}
_META = {"text", "cat", "flag_text"}


def _default_sigma(kind: str, value: float) -> float:
    return {"money": abs(value) * 0.05 + 1.0, "count": 0.5, "ratio": 0.05,
            "months": 0.5, "metric": abs(value) * 0.1 + 1.0}.get(kind, 1.0)


@dataclass(frozen=True)
class AttrSpec:
    name: str
    kind: str = "metric"          # money|count|ratio|months|metric (numérique) | text|cat (méta)
    unit: str = ""
    numeric: bool = True

    @staticmethod
    def of(name: str, kind: str = "metric", unit: str = "") -> "AttrSpec":
        return AttrSpec(name=name, kind=kind, unit=unit, numeric=kind in _NUMERIC)


@dataclass(frozen=True)
class RelationSpec:
    name: str
    inverse: str = ""
    semantics: str = "association"   # dependency|impact|composition|flow|ownership|association
    directed: bool = True


@dataclass(frozen=True)
class EntityType:
    name: str
    attrs: dict[str, AttrSpec] = field(default_factory=dict)
    description: str = ""


class Ontology:
    """Le SCHÉMA : quels types d'entités, d'attributs et de relations existent."""

    def __init__(self, entity_types: dict[str, EntityType], relation_types: dict[str, RelationSpec]) -> None:
        self.entity_types = entity_types
        self.relation_types = relation_types

    def entity_type(self, name: str) -> EntityType:
        if name not in self.entity_types:
            raise ValueError(f"type d'entité inconnu : {name!r}")
        return self.entity_types[name]

    def relation(self, name: str) -> RelationSpec:
        if name not in self.relation_types:
            raise ValueError(f"type de relation inconnu : {name!r}")
        return self.relation_types[name]

    # --- (dé)sérialisation du schéma : ontologie-comme-donnée ---
    def to_dict(self) -> dict:
        return {
            "entity_types": {n: {"description": t.description,
                                 "attrs": {a.name: {"kind": a.kind, "unit": a.unit}
                                           for a in t.attrs.values()}}
                             for n, t in self.entity_types.items()},
            "relation_types": {n: {"inverse": r.inverse, "semantics": r.semantics,
                                   "directed": r.directed} for n, r in self.relation_types.items()},
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Ontology":
        ets = {}
        for n, t in data.get("entity_types", {}).items():
            attrs = {an: AttrSpec.of(an, a.get("kind", "metric"), a.get("unit", ""))
                     for an, a in t.get("attrs", {}).items()}
            ets[n] = EntityType(name=n, attrs=attrs, description=t.get("description", ""))
        rts = {n: RelationSpec(name=n, inverse=r.get("inverse", ""),
                               semantics=r.get("semantics", "association"),
                               directed=r.get("directed", True))
               for n, r in data.get("relation_types", {}).items()}
        return cls(ets, rts)


@dataclass
class Entity:
    id: str
    type: str
    label: str = ""
    meta: dict = field(default_factory=dict)     # attributs textuels/catégoriels


class KnowledgeGraph:
    """Le graphe INSTANCIÉ : entités + relations, posé sur un WorldModel.

    Intégrité : add_entity/set_attr/relate valident contre l'ontologie (type, attribut,
    relation existent). Les attributs numériques sont des croyances ``id.attr``.
    """

    def __init__(self, ontology: Ontology, world: WorldModel | None = None) -> None:
        self.onto = ontology
        self.world = world or WorldModel()
        self.entities: dict[str, Entity] = {}
        self.edges: list[tuple[str, str, str]] = []          # (src, relation, dst)
        self._derived: list[tuple[str, Callable, list[str]]] = []   # attributs dérivés (pour re-simuler)

    # --- clé de croyance d'un attribut ---
    @staticmethod
    def key(entity_id: str, attr: str) -> str:
        return f"{entity_id}.{attr}"

    # --- entités ---
    def add_entity(self, etype: str, entity_id: str, label: str = "", *, now: float = 0.0,
                   values: dict | None = None, meta: dict | None = None) -> Entity:
        spec = self.onto.entity_type(etype)
        e = Entity(id=entity_id, type=etype, label=label or entity_id, meta=dict(meta or {}))
        self.entities[entity_id] = e
        for attr, val in (values or {}).items():
            self.set_attr(entity_id, attr, val, now=now, source="init")
        return e

    def set_attr(self, entity_id: str, attr: str, value, *, sigma: float | None = None,
                 now: float = 0.0, source: str = "mesure"):
        e = self._entity(entity_id)
        aspec = self.onto.entity_type(e.type).attrs.get(attr)
        if aspec is None:
            raise ValueError(f"{e.type} n'a pas d'attribut {attr!r}")
        if not aspec.numeric:
            e.meta[attr] = value
            return None
        sig = sigma if sigma is not None else _default_sigma(aspec.kind, float(value))
        return self.world.observe(self.key(entity_id, attr), float(value), sig,
                                  source=source, ts=now, unit=aspec.unit, kind=aspec.kind)

    def attr(self, entity_id: str, attr: str):
        return self.world.get(self.key(entity_id, attr))

    def value(self, entity_id: str, attr: str, default: float = 0.0) -> float:
        b = self.attr(entity_id, attr)
        return b.value if b else default

    # --- relations ---
    def relate(self, src: str, relation: str, dst: str) -> None:
        self.onto.relation(relation)               # valide le type de relation
        self._entity(src); self._entity(dst)       # valide les extrémités
        if (src, relation, dst) not in self.edges:
            self.edges.append((src, relation, dst))

    def neighbors(self, entity_id: str, relation: str | None = None, *, incoming: bool = False) -> list[str]:
        out = []
        for s, r, d in self.edges:
            if relation and r != relation:
                continue
            if not incoming and s == entity_id:
                out.append(d)
            elif incoming and d == entity_id:
                out.append(s)
        return out

    # --- attributs dérivés = simulation d'une chaîne causale ---
    def derive_attr(self, entity_id: str, attr: str, fn: Callable[[dict], float],
                    inputs: list[str], *, source: str = "dérivé"):
        """Déclare (et calcule) un attribut fonction d'autres attributs (mêmes clés
        ``id.attr``). Réutilise WorldModel.derive -> propagation d'incertitude."""
        e = self._entity(entity_id)
        aspec = self.onto.entity_type(e.type).attrs.get(attr)
        kind = aspec.kind if aspec else "metric"
        key = self.key(entity_id, attr)
        b = self.world.derive(key, fn, inputs, source=source, kind=kind,
                              unit=aspec.unit if aspec else "")
        self._derived.append((key, fn, inputs))
        return b

    def recompute(self) -> None:
        """Re-dérive toute la chaîne dans l'ordre de déclaration (suppose l'acyclicité)."""
        for key, fn, inputs in self._derived:
            b = self.world.derive(key, fn, inputs, source="re-dérivé",
                                  kind=self.world.get(key).kind if self.world.get(key) else "metric")

    def simulate(self, interventions: dict[str, float], now: float = 0.0) -> dict:
        """Applique des interventions (clés ``id.attr`` -> nouvelle valeur), re-dérive la
        chaîne, et renvoie l'avant/après des nœuds touchés. C'est la simulation de
        conséquences : « si le prix fournisseur monte, qu'arrive-t-il à la marge ? »."""
        before = {k: (b.value, b.sigma) for k, b in self.world.beliefs.items()}
        for key, val in interventions.items():
            b = self.world.get(key)
            # intervention counterfactuelle do(x=val) : on POSE la valeur (pas de fusion
            # bayésienne — c'est une hypothèse « et si », pas une nouvelle mesure).
            self.world.set(key, float(val), sigma=b.sigma if b else 1.0,
                           source="intervention", ts=now,
                           unit=b.unit if b else "", kind=b.kind if b else "metric")
        self.recompute()
        changed = {}
        for k, b in self.world.beliefs.items():
            if k not in before or abs(b.value - before[k][0]) > 1e-9:
                ov = before.get(k, (None, None))[0]
                changed[k] = {"avant": round(ov, 4) if ov is not None else None,
                              "apres": round(b.value, 4), "sigma": round(b.sigma, 4)}
        return changed

    # --- introspection ---
    def _entity(self, entity_id: str) -> Entity:
        if entity_id not in self.entities:
            raise ValueError(f"entité inconnue : {entity_id!r}")
        return self.entities[entity_id]

    def summary(self, now: float) -> dict:
        return {"entities": len(self.entities), "relations": len(self.edges),
                "by_type": {t: sum(1 for e in self.entities.values() if e.type == t)
                            for t in {e.type for e in self.entities.values()}},
                "beliefs": len(self.world.beliefs)}

    # --- persistance ---
    def to_dict(self) -> dict:
        return {"ontology": self.onto.to_dict(),
                "entities": [{"id": e.id, "type": e.type, "label": e.label, "meta": e.meta}
                             for e in self.entities.values()],
                "edges": self.edges, "world": self.world.to_dict()}


# ===================== HELYOS Ontology v1.0 (le schéma, comme donnée) =====================

def default_ontology() -> Ontology:
    """HELYOS Ontology v1.0 : les types d'entités et de relations du monde d'HELYOS.
    Curated depuis les 10 domaines (business, finance, trading, supply, engineering,
    manufacturing, human, infra, marché, connaissance). Extensible par édition."""
    A = AttrSpec.of
    ET = lambda name, desc, attrs: (name, EntityType(name, {a.name: a for a in attrs}, desc))

    entity_types = dict([
        ET("Company", "Une entreprise du portefeuille", [
            A("secteur", "cat"), A("mission", "text"),
            A("cash", "money", "€"), A("mrr", "money", "€/mois"), A("revenus", "money", "€/mois"),
            A("couts", "money", "€/mois"), A("marge", "ratio"), A("croissance", "ratio"),
            A("clients", "count"), A("churn", "ratio"), A("cac", "money", "€"), A("ltv", "money", "€"),
            A("runway_mois", "months", "mois"), A("risque", "ratio"), A("reputation", "ratio")]),
        ET("Product", "Un produit vendable", [
            A("prix", "money", "€"), A("cout_unitaire", "money", "€"), A("marge_unitaire", "ratio"),
            A("unites_mois", "count"), A("qualite", "ratio")]),
        ET("Service", "Un service / offre SaaS", [
            A("prix", "money", "€/mois"), A("cout_service", "money", "€/mois"), A("sla", "ratio")]),
        ET("Customer", "Un segment ou un client", [
            A("taille", "count"), A("valeur", "money", "€"), A("satisfaction", "ratio")]),
        ET("Supplier", "Un fournisseur", [
            A("pays", "cat"), A("unit_price", "money", "€"), A("moq", "count"),
            A("delai_jours", "count"), A("fiabilite", "ratio"), A("risque_geo", "ratio")]),
        ET("Employee", "Une compétence / un rôle", [
            A("role", "cat"), A("cout_mensuel", "money", "€/mois"), A("performance", "ratio"),
            A("disponible", "ratio")]),
        ET("Market", "Un marché / une opportunité de marché", [
            A("taille", "money", "€"), A("croissance", "ratio"), A("urgence", "ratio"),
            A("concurrence", "ratio"), A("sentiment", "ratio")]),
        ET("Asset", "Un actif tradable", [
            A("prix", "money"), A("volume", "metric"), A("volatilite", "ratio"),
            A("momentum", "ratio"), A("liquidite", "ratio")]),
        ET("Position", "Une position de trading", [
            A("taille", "money", "€"), A("entree", "money"), A("stop_loss", "money"),
            A("exposition", "ratio"), A("pnl", "money", "€")]),
        ET("Strategy", "Une stratégie (trading/business)", [
            A("performance", "ratio"), A("drawdown", "ratio"), A("probabilite", "ratio")]),
        ET("Opportunity", "Une opportunité de création de business", [
            A("taille_marche", "money", "€"), A("douleur", "ratio"), A("concurrence", "ratio"),
            A("cout_creation", "money", "€"), A("delai_lancement", "months", "mois"),
            A("prob_succes", "ratio"), A("score", "ratio")]),
        ET("Machine", "Une machine de production", [
            A("capacite", "count"), A("cout_horaire", "money", "€/h"), A("rendement", "ratio"),
            A("taux_defaut", "ratio")]),
        ET("Part", "Un objet/pièce d'ingénierie", [
            A("materiau", "cat"), A("masse_g", "metric", "g"), A("cout_fab", "money", "€"),
            A("resistance", "metric"), A("tolerance_mm", "metric", "mm")]),
        ET("Infrastructure", "Une infra numérique (SaaS)", [
            A("cout_cloud", "money", "€/mois"), A("utilisateurs", "count"),
            A("dispo", "ratio"), A("securite", "ratio")]),
        ET("Competitor", "Un concurrent", [
            A("part_marche", "ratio"), A("force", "ratio")]),
        ET("Knowledge", "Un nœud de connaissance (fait, techno, dépendance)", [
            A("confiance", "ratio")]),
    ])

    R = lambda name, inv, sem: (name, RelationSpec(name, inv, sem))
    relation_types = dict([
        R("owns", "owned_by", "ownership"),
        R("produces", "produced_by", "flow"),
        R("sells_to", "buys_from", "flow"),
        R("supplied_by", "supplies", "dependency"),
        R("employs", "employed_by", "ownership"),
        R("competes_with", "competes_with", "association"),
        R("targets", "targeted_by", "association"),
        R("depends_on", "required_by", "dependency"),
        R("impacts", "impacted_by", "impact"),
        R("uses", "used_by", "dependency"),
        R("trades", "traded_by", "flow"),
        R("composed_of", "part_of", "composition"),
        R("operated_by", "operates", "ownership"),
    ])
    return Ontology(entity_types, relation_types)
