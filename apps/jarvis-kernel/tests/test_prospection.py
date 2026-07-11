"""Tests du poste de prospection (le vrai outil de travail du Plan Cash)."""

from __future__ import annotations

import time
import unittest

from jarvis_kernel.business.prospection import ProspectionPipeline
from jarvis_kernel.context import build_default_context


class TestProspection(unittest.TestCase):
    def setUp(self) -> None:
        self.ctx = build_default_context()
        self.pipe = ProspectionPipeline(self.ctx.memory)

    def test_add_is_idempotent(self) -> None:
        self.pipe.add("Jean Martin", company="Plomberie Martin")
        self.pipe.add("Jean Martin", company="AUTRE")     # doublon ignoré
        self.assertEqual(len(self.pipe.list()), 1)
        self.assertEqual(self.pipe.list()[0].company, "Plomberie Martin")

    def test_invalid_status_rejected(self) -> None:
        self.pipe.add("Jean")
        with self.assertRaises(ValueError):
            self.pipe.set_status("Jean", "gagné_au_loto")
        with self.assertRaises(KeyError):
            self.pipe.set_status("Inconnu", "contacte")

    def test_followups_due_at_j3_then_j7(self) -> None:
        self.pipe.add("Jean")
        self.pipe.set_status("Jean", "contacte")
        now = time.time()
        self.assertEqual(self.pipe.due_followups(now=now), [])          # trop tôt
        due = self.pipe.due_followups(now=now + 3 * 86400 + 1)          # J+3
        self.assertEqual([(p.name, nxt) for p, nxt in due], [("Jean", "relance_1")])
        self.pipe.set_status("Jean", "relance_1")
        due = self.pipe.due_followups(now=time.time() + 4 * 86400 + 1)  # J+7
        self.assertEqual(due[0][1], "relance_2")

    def test_friday_stats_are_counted_not_embellished(self) -> None:
        for n, st in (("A", "contacte"), ("B", "repondu"), ("C", "client")):
            self.pipe.add(n)
            self.pipe.set_status(n, st)
        self.pipe.add("D")                                              # a_contacter
        s = self.pipe.stats()
        self.assertEqual((s["total"], s["contactes"], s["reponses"], s["clients"]),
                         (4, 3, 2, 1))

    def test_draft_mentions_prospect_and_sends_nothing(self) -> None:
        p = self.pipe.add("Jean Martin", company="Plomberie Martin")
        draft = self.pipe.draft_outreach(self.ctx.llm, p)
        self.assertIn("Jean Martin", draft)
        types = [e.action_type for e in self.ctx.governance.audit.tail(20)]
        self.assertNotIn("external_sensitive", types)                  # rédiger ≠ envoyer

    def test_jarvis_routing_and_add_parse(self) -> None:
        j = self.ctx.jarvis
        self.assertEqual(j.classify("qui dois-je relancer ?"), "prospection")
        self.assertEqual(j.classify("relance mes factures impayées"), "relance_factures")
        r = j.handle("ajoute un prospect : Jean Martin, Plomberie Martin, jm@ex.fr")
        self.assertEqual(r.intent, "prospection")
        self.assertIn("Jean Martin", r.text)
        self.assertEqual(len(self.pipe.list()), 1)

    def test_pulse_briefing_reminds_due_followups(self) -> None:
        self.pipe.add("Jean")
        self.pipe.set_status("Jean", "contacte")
        # antidate la dernière action : la relance devient due
        data = self.ctx.memory.recall("prospects", namespace="prospection")
        data["Jean"]["ts_last"] = time.time() - 4 * 86400
        self.ctx.memory.remember("prospects", data, namespace="prospection")
        self.ctx.connectors = [c for c in self.ctx.connectors if c.name != "market"]
        self.assertIn("relance(s) de prospection", self.ctx.pulse.briefing())


if __name__ == "__main__":
    unittest.main()
