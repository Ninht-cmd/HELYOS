"""Tests de l'InvoiceReminderAgent (HELYOS v1) — rédaction A1, envoi gouverné A2/GR-2."""

import unittest

from jarvis_kernel.agents.invoice_reminder import Invoice, InvoiceReminderAgent, _tone_for
from jarvis_kernel.context import build_default_context
from jarvis_kernel.governance.autonomy import AutonomyLevel
from jarvis_kernel.governance.policy import Decision

INVOICES = [
    Invoice(client="Boulangerie Martin", amount_eur=120.0, days_late=10, email="a@x.fr", ref="F-001"),
    Invoice(client="Garage Dupont", amount_eur=890.0, days_late=30, email="b@x.fr", ref="F-002"),
    Invoice(client="SCI Leroy", amount_eur=2400.0, days_late=60, email="c@x.fr", ref="F-003"),
]


class TestInvoiceReminder(unittest.TestCase):
    def setUp(self):
        self.ctx = build_default_context()
        self.agent = InvoiceReminderAgent()

    def test_registered_in_context(self):
        self.assertIn("invoice_reminder", self.ctx.registry)

    def test_tone_escalates_with_lateness(self):
        self.assertEqual(_tone_for(10), "courtois")
        self.assertEqual(_tone_for(30), "ferme")
        self.assertEqual(_tone_for(60), "dernier_rappel")

    def test_draft_blocked_below_a1(self):
        v, r = self.agent.draft_reminders(self.ctx.governance, INVOICES, granted=AutonomyLevel.A0)
        self.assertEqual(v.decision, Decision.REQUIRE_VALIDATION)
        self.assertEqual(r, [])

    def test_draft_produces_one_reminder_per_invoice(self):
        v, reminders = self.agent.draft_reminders(
            self.ctx.governance, INVOICES, granted=AutonomyLevel.A1, memory=self.ctx.memory)
        self.assertEqual(v.decision, Decision.ALLOW)
        self.assertEqual(len(reminders), 3)
        self.assertEqual([r.tone for r in reminders], ["courtois", "ferme", "dernier_rappel"])
        self.assertTrue(all(r.subject and r.body for r in reminders))
        self.assertIsNotNone(self.ctx.memory.recall("dernieres_relances", namespace="factures"))

    def test_send_requires_validation_even_at_a5(self):
        _, reminders = self.agent.draft_reminders(self.ctx.governance, INVOICES, granted=AutonomyLevel.A1)
        v = self.agent.propose_send(self.ctx.governance, reminders[0],
                                    granted=AutonomyLevel.A5, validated=False)
        self.assertEqual(v.decision, Decision.REQUIRE_VALIDATION)
        self.assertEqual(v.rule, "GR-2")

    def test_send_allowed_when_validated(self):
        _, reminders = self.agent.draft_reminders(self.ctx.governance, INVOICES, granted=AutonomyLevel.A1)
        v = self.agent.propose_send(self.ctx.governance, reminders[0],
                                    granted=AutonomyLevel.A2, validated=True)
        self.assertEqual(v.decision, Decision.ALLOW)


if __name__ == "__main__":
    unittest.main()
