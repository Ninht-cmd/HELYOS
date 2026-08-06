"""Tests de la couche AGENT supply chain : vraies données CSV + proposition gouvernée."""

from __future__ import annotations

import unittest
from pathlib import Path

from jarvis_kernel.governance.autonomy import AutonomyLevel
from jarvis_kernel.governance.service import GovernanceService
from jarvis_kernel.world.domains.supply_chain_agent import (advise, learn_suppliers,
                                                            read_receptions_csv)

CSV = Path(__file__).resolve().parents[3] / "data" / "receptions.csv"
PARAMS = dict(demand=10, sigma_demand=2, sigma_lead_time=1, service_level=0.95,
              annual_demand=3650, order_cost=50, holding_cost=2, stockout_cost=20)


class TestRealDataConnector(unittest.TestCase):
    def test_reads_real_csv(self) -> None:
        rows = read_receptions_csv(CSV)
        self.assertGreater(len(rows), 20)
        suppliers = {s for _d, s, _lt in rows}
        self.assertIn("FRN-07", suppliers)
        self.assertIn("FRN-12", suppliers)

    def test_learns_per_supplier_from_data(self) -> None:
        sup = learn_suppliers(read_receptions_csv(CSV), prior=9.0)
        self.assertAlmostEqual(sup["FRN-07"]["learned"], 14.0, delta=0.6)   # dérive réelle
        self.assertAlmostEqual(sup["FRN-12"]["learned"], 7.2, delta=0.8)    # alternatif plus rapide


class TestGovernedAgent(unittest.TestCase):
    def setUp(self) -> None:
        self.gov = GovernanceService()
        self.rows = read_receptions_csv(CSV)

    def test_advice_proposes_and_requires_validation(self) -> None:
        out = advise("FRN-07", self.rows, PARAMS, prior_lead_time=9.0,
                     governance=self.gov, granted=AutonomyLevel.A2)
        # comportement d'agent : impact chiffré + alternative trouvée DANS les données
        self.assertGreater(out["rop_after"], out["rop_before"])
        self.assertTrue(out["alternatives"])
        self.assertEqual(out["alternatives"][0]["fournisseur"], "FRN-12")
        # GOUVERNANCE : l'action externe n'est JAMAIS autonome -> validation requise (GR-2)
        self.assertEqual(out["external_action"]["decision"], "require_validation")
        self.assertEqual(out["external_action"]["rule"], "GR-2")
        self.assertIn("attends ta validation", out["narrative"])

    def test_validated_action_still_governed_not_autonomous(self) -> None:
        # même à A5, une action externe non validée reste en validation requise (GR-2 prime)
        out = advise("FRN-07", self.rows, PARAMS, prior_lead_time=9.0,
                     governance=self.gov, granted=AutonomyLevel.A5)
        self.assertEqual(out["external_action"]["decision"], "require_validation")


if __name__ == "__main__":
    unittest.main()
