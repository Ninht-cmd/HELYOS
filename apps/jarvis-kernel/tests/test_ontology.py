"""Tests de l'ontologie : intégrité du schéma + simulation multi-sauts chiffrée.

On prouve que le graphe n'est pas un diagramme : il valide les types, porte des
croyances μ±σ, et propage une intervention le long d'une chaîne causale.
"""

from __future__ import annotations

import unittest

from jarvis_kernel.world.ontology import KnowledgeGraph, default_ontology

NOW = 1_000_000.0


class TestOntologySchema(unittest.TestCase):
    def test_schema_has_core_domains(self) -> None:
        o = default_ontology()
        for t in ("Company", "Supplier", "Product", "Market", "Asset", "Machine", "Opportunity"):
            self.assertIn(t, o.entity_types)
        for r in ("supplied_by", "impacts", "depends_on", "produces", "competes_with"):
            self.assertIn(r, o.relation_types)

    def test_schema_roundtrip(self) -> None:
        o = default_ontology()
        o2 = type(o).from_dict(o.to_dict())
        self.assertEqual(set(o.entity_types), set(o2.entity_types))
        self.assertEqual(o2.entity_type("Company").attrs["cash"].kind, "money")


class TestGraphIntegrity(unittest.TestCase):
    def setUp(self) -> None:
        self.g = KnowledgeGraph(default_ontology())

    def test_unknown_type_rejected(self) -> None:
        with self.assertRaises(ValueError):
            self.g.add_entity("Licorne", "x", now=NOW)

    def test_unknown_attr_rejected(self) -> None:
        self.g.add_entity("Company", "c1", now=NOW)
        with self.assertRaises(ValueError):
            self.g.set_attr("c1", "couleur_preferee", 3, now=NOW)

    def test_unknown_relation_rejected(self) -> None:
        self.g.add_entity("Company", "c1", now=NOW)
        self.g.add_entity("Supplier", "s1", now=NOW)
        with self.assertRaises(ValueError):
            self.g.relate("c1", "adore", "s1")

    def test_numeric_attr_is_a_belief_meta_is_not(self) -> None:
        self.g.add_entity("Supplier", "s1", now=NOW,
                          values={"unit_price": 2.0}, meta={"pays": "Chine"})
        self.assertIsNotNone(self.g.attr("s1", "unit_price"))       # croyance
        self.g.set_attr("s1", "pays", "Vietnam", now=NOW)           # texte -> meta
        self.assertEqual(self.g.entities["s1"].meta["pays"], "Vietnam")
        self.assertIsNone(self.g.attr("s1", "pays"))                # pas de croyance pour du texte


class TestSimulationChain(unittest.TestCase):
    """L'exemple du fondateur : fournisseur -> coût produit -> marge entreprise."""

    def setUp(self) -> None:
        self.g = KnowledgeGraph(default_ontology())
        self.g.add_entity("Supplier", "foxconn", "Foxconn", now=NOW,
                          values={"unit_price": 2.0}, meta={"pays": "Chine"})
        self.g.add_entity("Product", "coque", "Coque téléphone", now=NOW,
                          values={"prix": 15.0, "unites_mois": 100})
        self.g.add_entity("Company", "coques_biz", "Business coques", now=NOW,
                          values={"revenus": 1500.0})
        self.g.relate("coque", "supplied_by", "foxconn")
        self.g.relate("coques_biz", "produces", "coque")
        k = self.g.key
        # coût unitaire du produit = 1.6 × prix fournisseur (marge d'assemblage)
        self.g.derive_attr("coque", "cout_unitaire", lambda m: 1.6 * m[k("foxconn", "unit_price")],
                           [k("foxconn", "unit_price")])
        # coûts entreprise = coût unitaire × unités/mois
        self.g.derive_attr("coques_biz", "couts",
                           lambda m: m[k("coque", "cout_unitaire")] * m[k("coque", "unites_mois")],
                           [k("coque", "cout_unitaire"), k("coque", "unites_mois")])
        # marge entreprise = (revenus - coûts) / revenus
        self.g.derive_attr("coques_biz", "marge",
                           lambda m: (m[k("coques_biz", "revenus")] - m[k("coques_biz", "couts")])
                                     / max(m[k("coques_biz", "revenus")], 1e-6),
                           [k("coques_biz", "revenus"), k("coques_biz", "couts")])

    def test_baseline_margin(self) -> None:
        k = self.g.key
        # coût unit = 1.6×2 = 3.2 ; coûts = 3.2×100 = 320 ; marge = (1500-320)/1500 = 0.7867
        self.assertAlmostEqual(self.g.value("coque", "cout_unitaire"), 3.2, places=6)
        self.assertAlmostEqual(self.g.value("coques_biz", "couts"), 320.0, places=6)
        self.assertAlmostEqual(self.g.value("coques_biz", "marge"), (1500 - 320) / 1500, places=6)

    def test_supplier_price_shock_propagates_to_margin(self) -> None:
        k = self.g.key
        before = self.g.value("coques_biz", "marge")
        # choc : le prix fournisseur double (2 -> 4)
        changed = self.g.simulate({k("foxconn", "unit_price"): 4.0}, now=NOW)
        after = self.g.value("coques_biz", "marge")
        # coût unit -> 6.4 ; coûts -> 640 ; marge -> (1500-640)/1500 = 0.5733
        self.assertAlmostEqual(self.g.value("coque", "cout_unitaire"), 6.4, places=6)
        self.assertAlmostEqual(after, (1500 - 640) / 1500, places=6)
        self.assertLess(after, before)                       # la marge s'effondre
        # la chaîne entière a bougé (3 nœuds touchés au moins)
        self.assertIn(k("coques_biz", "marge"), changed)
        self.assertIn(k("coque", "cout_unitaire"), changed)

    def test_uncertainty_propagates(self) -> None:
        # la marge dérivée porte une incertitude > 0 (propagée du prix fournisseur)
        b = self.g.attr("coques_biz", "marge")
        self.assertGreater(b.sigma, 0.0)


if __name__ == "__main__":
    unittest.main()
