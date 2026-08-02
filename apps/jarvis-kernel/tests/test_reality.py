"""Tests de la Reality Layer v1.1 : ressources, objectifs, événements, décision, H=N."""

from __future__ import annotations

import unittest

from jarvis_kernel.world.ontology import KnowledgeGraph, default_ontology
from jarvis_kernel.world.reality import (Response, apply_event, company_utility,
                                         feasible, goal_attainment, resource_pool,
                                         respond, rollout)

NOW = 1_000_000.0


def _biz_graph() -> KnowledgeGraph:
    g = KnowledgeGraph(default_ontology())
    g.add_entity("Supplier", "sup", "Fournisseur", now=NOW, values={"unit_price": 2.0})
    g.add_entity("Product", "prod", "Produit", now=NOW, values={"unites_mois": 100})
    g.add_entity("Company", "biz", "Business", now=NOW,
                 values={"revenus": 1500.0, "cash": 3000.0, "croissance": 0.1, "risque": 0.3})
    g.relate("prod", "supplied_by", "sup")
    k = g.key
    g.derive_attr("prod", "cout_unitaire", lambda m: 1.6 * m[k("sup", "unit_price")], [k("sup", "unit_price")])
    g.derive_attr("biz", "couts",
                  lambda m: m[k("prod", "cout_unitaire")] * m[k("prod", "unites_mois")],
                  [k("prod", "cout_unitaire"), k("prod", "unites_mois")])
    g.derive_attr("biz", "marge",
                  lambda m: (m[k("biz", "revenus")] - m[k("biz", "couts")]) / max(m[k("biz", "revenus")], 1e-6),
                  [k("biz", "revenus"), k("biz", "couts")])
    return g


class TestOntologyV11(unittest.TestCase):
    def test_new_types_present(self) -> None:
        o = default_ontology()
        for t in ("Goal", "Resource", "Event", "Process", "Project", "Contract",
                  "Material", "Technology", "Location", "Risk"):
            self.assertIn(t, o.entity_types)
        self.assertGreaterEqual(len(o.entity_types), 25)          # ~26 types


class TestResourceModel(unittest.TestCase):
    def test_pool_and_feasibility(self) -> None:
        g = KnowledgeGraph(default_ontology())
        g.add_entity("Resource", "cash", now=NOW, values={"quantite": 5000, "disponibilite": 1.0},
                     meta={"kind": "financial"})
        g.add_entity("Resource", "devs", now=NOW, values={"quantite": 2, "disponibilite": 0.5},
                     meta={"kind": "human"})
        pool = resource_pool(g)
        self.assertEqual(pool["financial"], 5000.0)
        self.assertEqual(pool["human"], 1.0)                      # 2 × 0.5 dispo
        ok, lacks = feasible(g, {"financial": 3000, "human": 3})
        self.assertFalse(ok)
        self.assertEqual(lacks, {"human": 2.0})                   # il manque 2 humains


class TestGoalSystem(unittest.TestCase):
    def test_goal_attainment_from_targets(self) -> None:
        g = _biz_graph()
        g.add_entity("Goal", "obj", "Marge saine", now=NOW,
                     values={"priorite": 0.9, "horizon_mois": 12},
                     meta={"targets": {"biz.marge": 0.9}})
        # marge courante ≈ 0.787 ; cible 0.9 → atteinte ≈ 0.874
        self.assertAlmostEqual(goal_attainment(g, "obj", NOW), round((1500 - 320) / 1500 / 0.9, 3), places=2)


class TestEventDrivesDecision(unittest.TestCase):
    def test_event_propagates_and_triggers_new_decision(self) -> None:
        g = _biz_graph()
        u_before, _ = company_utility(g, "biz", NOW)
        # ÉVÉNEMENT : le fournisseur double son prix
        changed = apply_event(g, {g.key("sup", "unit_price"): 4.0}, NOW)
        self.assertIn(g.key("biz", "marge"), changed)             # propagation causale
        u_after, _ = company_utility(g, "biz", NOW)
        self.assertLess(u_after, u_before)                        # l'utilité chute
        # NOUVELLE DÉCISION : classer les réponses
        options = [
            Response("Renégocier le fournisseur", [(g.key("prod", "cout_unitaire"), "mul", 0.8)], cost=0.01),
            Response("Monter le prix produit (+20%)", [(g.key("biz", "revenus"), "mul", 1.2)], cost=0.02),
            Response("Embaucher (infaisable)", [], needs={"human": 5}),
        ]
        ranked = respond(g, "biz", options, NOW)
        self.assertEqual(len(ranked), 3)
        self.assertTrue(ranked[0]["faisable"])
        self.assertIsNotNone(ranked[0]["gain"])
        self.assertFalse(ranked[-1]["faisable"])                  # l'option sans ressource est écartée


class TestRolloutHN(unittest.TestCase):
    def test_multistep_trajectory(self) -> None:
        g = _biz_graph()
        steps = [
            ("choc fournisseur", {g.key("sup", "unit_price"): 4.0}),
            ("réponse : +20% prix", {g.key("biz", "revenus"): 1800.0}),
        ]
        traj = rollout(g, "biz", steps, NOW)
        self.assertEqual([p["pas"] for p in traj], [0, 1, 2])
        self.assertLess(traj[1]["u"], traj[0]["u"])               # le choc baisse U
        self.assertGreater(traj[2]["u"], traj[1]["u"])            # la réponse la remonte
        # le graphe d'origine n'a pas été muté par le rollout (clone)
        self.assertAlmostEqual(g.value("sup", "unit_price"), 2.0, places=6)


if __name__ == "__main__":
    unittest.main()
