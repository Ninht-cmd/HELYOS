"""CRM / Sales réel : la boucle end-to-end gouvernée et scopée IAM.

Test d'acceptation : lead → qualification → opportunité → e-mail → GOUVERNANCE (GR-2) → envoi
validé → réponse → vente → Outcome → Mémoire. CRM = ACTIVE seulement quand la boucle a tourné.
"""

from __future__ import annotations

import unittest

from jarvis_kernel.business.crm import CRMWorkflow, qualify_score
from jarvis_kernel.business.orders import OrderBook
from jarvis_kernel.governance.autonomy import AutonomyLevel
from jarvis_kernel.governance.service import GovernanceService
from jarvis_kernel.iam import IAM, seed_default_iam
from jarvis_kernel.memory import build_memory
from jarvis_kernel.operations import OperationsController

LEAD = "Boulangerie Martin"


def _setup():
    mem = build_memory("memory")
    iam = seed_default_iam(IAM())
    ops = OperationsController()
    ops.register_agent("sales_agent")
    gov = GovernanceService(operations=ops)
    return mem, iam, ops, gov


class TestAcceptanceLoop(unittest.TestCase):
    def test_lead_to_outcome_full_cycle(self) -> None:
        mem, iam, ops, gov = _setup()
        crm = CRMWorkflow(mem, iam=iam, governance=gov)

        # 1. lead réel stocké (Sales Agent, scope IAM)
        r = crm.ingest_lead("sales_agent", LEAD, company="Martin SARL",
                            contact="martin@ex.fr", note="besoin d'un devis, assez urgent")
        self.assertTrue(r["allowed"])

        # 2. qualification (déterministe, exploitable)
        q = crm.qualify("sales_agent", LEAD)
        self.assertEqual(q["stage"], "qualified")
        self.assertGreaterEqual(q["qualification"], 60)

        # 3. opportunité + 4. e-mail préparé
        crm.create_opportunity(LEAD, 490)
        p = crm.prepare_email("sales_agent", LEAD)
        self.assertTrue(p["allowed"] and p["draft"])

        # 5. GOUVERNANCE : sans validation → REQUIRE_VALIDATION (GR-2), rien n'est envoyé
        s1 = crm.request_send("sales_agent", LEAD, validated=False, granted=AutonomyLevel.A3)
        self.assertEqual(s1["final"], "REQUIRE_VALIDATION")
        self.assertEqual(s1["policy"], "GR-2")

        # …avec validation humaine → ALLOW (envoyé)
        s2 = crm.request_send("sales_agent", LEAD, validated=True, granted=AutonomyLevel.A3)
        self.assertEqual(s2["final"], "ALLOW")

        # 6. réponse → 7. clôture (vente) → Outcome → Mémoire
        crm.record_response(LEAD, positive=True)
        c = crm.close("sales_agent", LEAD, won=True, amount=490)
        self.assertTrue(c["allowed"])

        snap = crm.snapshot()
        self.assertTrue(snap["active"])                    # la boucle a produit un Outcome → ACTIVE
        self.assertEqual(snap["won"], 1)
        self.assertEqual(snap["revenue_eur"], 490)
        # la vente alimente le carnet de commandes (à encaisser) — flux réel vers le cockpit
        self.assertGreaterEqual(OrderBook(mem).summary()["ventes"], 1)


class TestIamScoping(unittest.TestCase):
    def test_agent_without_crm_permission_denied(self) -> None:
        mem, iam, ops, gov = _setup()
        crm = CRMWorkflow(mem, iam=iam, governance=gov)
        # finance_agent (rôle Finance) n'a pas crm.update → refus IAM
        r = crm.ingest_lead("finance_agent", "Lead X", company="X")
        self.assertFalse(r["allowed"])
        self.assertEqual(r["policy"], "IAM-RBAC")


class TestSuspendedAgentBlocked(unittest.TestCase):
    def test_suspended_sales_agent_cannot_send(self) -> None:
        mem, iam, ops, gov = _setup()
        crm = CRMWorkflow(mem, iam=iam, governance=gov)
        crm.ingest_lead("sales_agent", LEAD, contact="a@b.fr")
        ops.enter_safe_mode("incident Sales", scope=["sales_agent"])
        s = crm.request_send("sales_agent", LEAD, validated=True, granted=AutonomyLevel.A3)
        self.assertEqual(s["final"], "DENY")
        self.assertEqual(s["policy"], "OPS-SUSPENDED")     # suspension > permission IAM


class TestQualification(unittest.TestCase):
    def test_score_reflects_signals(self) -> None:
        hi, stage_hi = qualify_score("ACME", "a@b.fr", "besoin urgent, budget prêt")
        lo, stage_lo = qualify_score("", "", "")
        self.assertGreater(hi, lo)
        self.assertEqual(stage_hi, "qualified")
        self.assertNotEqual(stage_lo, "qualified")


if __name__ == "__main__":
    unittest.main()
