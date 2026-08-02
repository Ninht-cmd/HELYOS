"""Domaine ENGINEERING / MANUFACTURING — vraies lois méca & production.

Équations correctes (testées) : contrainte de flexion, coefficient de sécurité,
dilatation thermique, OEE (rendement global), cadence, coût unitaire de fabrication.
Enrichit les types ``Machine`` et ``Part`` avec leurs variables métier.
"""

from __future__ import annotations

from ..ontology import AttrSpec, EntityType
from . import Domain

_A = AttrSpec.of


# ------------------------------------------------------------------ équations méca
def bending_stress(moment: float, dist_neutral_axis: float, inertia: float) -> float:
    """Contrainte de flexion σ = M·c / I  (M moment, c distance à la fibre neutre, I inertie)."""
    return moment * dist_neutral_axis / inertia if inertia else float("inf")


def safety_factor(yield_strength: float, applied_stress: float) -> float:
    """Coefficient de sécurité = limite élastique / contrainte appliquée."""
    return yield_strength / applied_stress if applied_stress else float("inf")


def thermal_expansion(length: float, alpha: float, delta_t: float) -> float:
    """Dilatation ΔL = L·α·ΔT."""
    return length * alpha * delta_t


# ------------------------------------------------------------------ équations manufacturing
def oee(availability: float, performance: float, quality: float) -> float:
    """Rendement global (OEE) = disponibilité × performance × qualité."""
    return availability * performance * quality


def throughput(capacity: float, oee_value: float) -> float:
    """Cadence effective = capacité nominale × OEE."""
    return capacity * oee_value


def unit_cost(material: float, assembly: float, machine_hourly: float, cycle_h: float) -> float:
    """Coût unitaire = matière + assemblage + (coût horaire machine × temps de cycle)."""
    return material + assembly + machine_hourly * cycle_h


# ------------------------------------------------------------------ domaine
ENGINEERING = Domain(
    name="engineering",
    entity_types={
        "Machine": EntityType("Machine",
            {a.name: a for a in [
                _A("disponibilite", "ratio"), _A("performance", "ratio"), _A("qualite", "ratio"),
                _A("oee", "ratio"), _A("cycle_time_h", "metric", "h"),
                _A("energie_kw", "metric", "kW"), _A("maintenance_pct", "ratio")]},
            "Machine de production (enrichie : OEE, cadence, énergie)"),
        "Part": EntityType("Part",
            {a.name: a for a in [
                _A("contrainte_max", "metric", "MPa"), _A("limite_elastique", "metric", "MPa"),
                _A("coef_securite", "ratio"), _A("temperature", "metric", "°C"),
                _A("fatigue_cycles", "metric")]},
            "Pièce d'ingénierie (enrichie : contraintes, sécurité, fatigue)"),
    },
    equations={"bending_stress": bending_stress, "safety_factor": safety_factor,
               "thermal_expansion": thermal_expansion, "oee": oee, "throughput": throughput,
               "unit_cost": unit_cost},
)


def wire_machine(graph, machine_id: str) -> None:
    """OEE et cadence effective dérivés (disponibilité × performance × qualité)."""
    k = graph.key
    graph.derive_attr(machine_id, "oee",
                      lambda m: oee(m[k(machine_id, "disponibilite")], m[k(machine_id, "performance")],
                                    m[k(machine_id, "qualite")]),
                      [k(machine_id, "disponibilite"), k(machine_id, "performance"),
                       k(machine_id, "qualite")])


def wire_part_safety(graph, part_id: str) -> None:
    """Coefficient de sécurité dérivé de la limite élastique et de la contrainte max."""
    k = graph.key
    graph.derive_attr(part_id, "coef_securite",
                      lambda m: safety_factor(m[k(part_id, "limite_elastique")],
                                              m[k(part_id, "contrainte_max")]),
                      [k(part_id, "limite_elastique"), k(part_id, "contrainte_max")])
