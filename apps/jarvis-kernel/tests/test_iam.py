"""IAM entreprise v1 : RBAC + ABAC + ReBAC + business scopes + profils IA + break-glass.

Les 11 tests d'acceptation exigés + persistance. Règle : permission effective = identité ∩
profil IA ∩ business ∩ gouvernance ∩ operations ; une identité ne s'accorde jamais plus de droits.
"""

from __future__ import annotations

import unittest

from jarvis_kernel.governance.autonomy import AutonomyLevel
from jarvis_kernel.governance.service import GovernanceService
from jarvis_kernel.iam import IAM, seed_default_iam, enforce
from jarvis_kernel.operations import OperationsController


class TestAuthorization(unittest.TestCase):
    def setUp(self) -> None:
        self.iam = seed_default_iam(IAM())

    def test_1_sales_employee_reads_own_crm_allow(self) -> None:
        d = self.iam.authorize("thomas", "crm.read", "prospect:847@BUS-001", {"business": "BUS-001"})
        self.assertTrue(d.allowed, d.reason)

    def test_2_sales_employee_payroll_deny(self) -> None:
        d = self.iam.authorize("thomas", "payroll.read", context={"business": "BUS-001"})
        self.assertFalse(d.allowed)
        self.assertEqual(d.policy, "IAM-RBAC")

    def test_3_sales_agent_email_prepare_allow(self) -> None:
        d = self.iam.authorize("sales_agent", "email.prepare", context={"business": "BUS-001"})
        self.assertTrue(d.allowed, d.reason)

    def test_4_sales_agent_bank_transfer_deny(self) -> None:
        d = self.iam.authorize("sales_agent", "bank.transfer", "bank_account:BUS-001",
                               {"business": "BUS-001", "amount": 1000})
        self.assertFalse(d.allowed)

    def test_9_cross_business_records_deny(self) -> None:
        d = self.iam.authorize("alex", "records.read", "records:BUS-002", {"business": "BUS-002"})
        self.assertFalse(d.allowed)
        self.assertEqual(d.policy, "IAM-SCOPE")

    def test_11_ai_cannot_modify_own_permission(self) -> None:
        d = self.iam.authorize("sales_agent", "iam.grant", "identity:sales_agent",
                               {"target": "sales_agent"})
        self.assertFalse(d.allowed)
        self.assertEqual(d.policy, "IAM-SELF")


class TestManualTakeover(unittest.TestCase):
    def setUp(self) -> None:
        self.iam = seed_default_iam(IAM())

    def test_8_authorized_takeover_allows_and_audits(self) -> None:
        before = len(self.iam.audit())
        d = self.iam.authorize_takeover("thomas", "BUS-001")
        self.assertTrue(d.allowed)
        self.assertGreater(len(self.iam.audit()), before)          # AuditEvent produit

    def test_7_takeover_out_of_scope_deny(self) -> None:
        d = self.iam.authorize_takeover("alex", "BUS-002")          # alex n'est pas dans BUS-002
        self.assertFalse(d.allowed)
        self.assertEqual(d.policy, "IAM-SCOPE")


class TestBreakGlass(unittest.TestCase):
    def test_10_emergency_grant_expires_automatically(self) -> None:
        t = [1000.0]
        iam = seed_default_iam(IAM(clock=lambda: t[0]))
        iam.grant_emergency("thomas", {"finance.transfer"}, "incident bancaire", ttl_seconds=100)
        d1 = iam.authorize("thomas", "finance.transfer", "bank_account:BUS-001",
                           {"business": "BUS-001", "amount": 100})
        self.assertTrue(d1.allowed, "grant actif → autorisé")
        t[0] = 1200.0                                              # au-delà de l'expiration
        d2 = iam.authorize("thomas", "finance.transfer", "bank_account:BUS-001",
                           {"business": "BUS-001", "amount": 100})
        self.assertFalse(d2.allowed, "grant expiré → accès auto-révoqué")


class TestFullPipeline(unittest.TestCase):
    """enforce : IAM autorise, PUIS gouvernance (GR-x) et operations (suspension)."""

    def test_5_finance_agent_transfer_requires_validation_gr7(self) -> None:
        iam = seed_default_iam(IAM())
        gov = GovernanceService()
        res = enforce(iam, gov, "finance_agent", "finance.transfer", "bank_account:BUS-001",
                      {"business": "BUS-001", "amount": 3000, "autonomy": "A5"}, granted=AutonomyLevel.A5)
        self.assertEqual(res["final"], "REQUIRE_VALIDATION")       # A5 ne saute pas GR-7
        self.assertEqual(res["policy"], "GR-7")

    def test_6_suspended_agent_denied_even_if_iam_allows(self) -> None:
        iam = seed_default_iam(IAM())
        ops = OperationsController()
        ops.register_agent("sales_agent")
        ops.enter_safe_mode("incident Sales", scope=["sales_agent"])
        gov = GovernanceService(operations=ops)
        res = enforce(iam, gov, "sales_agent", "email.send", "prospect:847@BUS-001",
                      {"business": "BUS-001", "validated": True}, granted=AutonomyLevel.A3)
        self.assertEqual(res["final"], "DENY")
        self.assertEqual(res["policy"], "OPS-SUSPENDED")           # suspendu > permission IAM


class TestPersistence(unittest.TestCase):
    def test_roundtrip_preserves_authorization(self) -> None:
        iam = seed_default_iam(IAM())
        d1 = iam.authorize("thomas", "crm.read", context={"business": "BUS-001"})
        iam2 = IAM.from_dict(iam.to_dict())
        d2 = iam2.authorize("thomas", "crm.read", context={"business": "BUS-001"})
        self.assertEqual(d1.allowed, d2.allowed)
        self.assertTrue(d2.allowed)
        self.assertTrue(all(iam2.readiness().values()))


if __name__ == "__main__":
    unittest.main()
