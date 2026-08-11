"""Manual Override + SAFE MODE : exploitation AI-first, fail-operational.

Test d'acceptation (le flux exact) + les 6 invariants + la garde de gouvernance :
AI_FIRST → incident → SAFE_MODE → agents suspendus → services métier en ligne → l'humain
opère (audité) → [rendre la main] → RECOVERY (relecture → MemoryEvent) → AI_FIRST.
"""

from __future__ import annotations

import unittest

from jarvis_kernel.governance.autonomy import AutonomyLevel
from jarvis_kernel.governance.policy import Action, ActionType, Decision
from jarvis_kernel.governance.service import GovernanceService
from jarvis_kernel.operations import (AI_FIRST, ONLINE, RUNNING, SAFE_MODE, SUSPENDED,
                                      OperationsController)
from jarvis_kernel.world.memory_store import UnifiedMemory


def _ops(mem=None):
    ops = OperationsController(memory=mem)
    for a in ("sales_agent", "finance_agent"):
        ops.register_agent(a)
    return ops


class TestAcceptanceFlow(unittest.TestCase):
    def test_full_incident_to_recovery_cycle(self) -> None:
        mem = UnifiedMemory()
        ops = _ops(mem)
        gov = GovernanceService(operations=ops)
        self.assertEqual(ops.mode, AI_FIRST)

        # 1. incident critique → SAFE MODE global
        ops.enter_safe_mode("panne orchestration IA", actor="system")
        self.assertEqual(ops.mode, SAFE_MODE)
        # agents suspendus
        self.assertEqual(ops.agent_state("sales_agent"), SUSPENDED)
        self.assertEqual(ops.agent_state("finance_agent"), SUSPENDED)
        # services métier / données / audit TOUJOURS en ligne (invariant 1)
        for s in ("crm", "finance_data", "business_db", "audit", "memory"):
            self.assertEqual(ops.services[s]["state"], ONLINE, s)

        # 5. un agent suspendu ne peut plus exécuter (envoi/paiement/publication)
        v = gov.submit(Action(type=ActionType.EXTERNAL_SENSITIVE, actor="sales_agent",
                              description="envoyer un email", sensitive=True), AutonomyLevel.A5)
        self.assertIs(v.decision, Decision.DENY)
        self.assertEqual(v.rule, "OPS-SUSPENDED")

        # 1 & 2. mais lire les données métier reste possible (mêmes services, mêmes données)
        r = gov.submit(Action(type=ActionType.ANALYZE, actor="sales_agent",
                              description="lire le CRM"), AutonomyLevel.A1)
        self.assertIs(r.decision, Decision.ALLOW)

        # 3. l'humain opère → who/what/when/why enregistrés
        h = ops.human_action("emeric", "relance manuelle du client X", "l'agent est suspendu")
        self.assertEqual(h.who, "emeric")
        self.assertTrue(h.what and h.why and h.ts)

        # rendre la main : passage OBLIGÉ par RECOVERY + MemoryEvent (invariants 4 & 6)
        before_events = len(mem.events)
        res = ops.return_to_ai("emeric", "incident résolu", reread=lambda: {"crm": "1 relance manuelle"})
        self.assertEqual(ops.mode, AI_FIRST)
        self.assertIsNotNone(res["memory_event"])
        self.assertGreater(len(mem.events), before_events)          # MemoryEvent produit → Planner replanifie
        self.assertTrue(any("ops:handover" in e.entities for e in mem.events.values()))
        # agents repris
        self.assertEqual(ops.agent_state("sales_agent"), RUNNING)
        # retour explicite et audité
        self.assertEqual(ops.log[-1].kind, "return_ai")
        self.assertEqual(ops.log[-1].who, "emeric")


class TestGranularity(unittest.TestCase):
    def test_sales_incident_does_not_stop_finance(self) -> None:
        ops = _ops()
        gov = GovernanceService(operations=ops)
        ops.enter_safe_mode("incident Sales", actor="system", scope=["sales_agent"])
        self.assertEqual(ops.agent_state("sales_agent"), SUSPENDED)
        self.assertEqual(ops.agent_state("finance_agent"), RUNNING)   # non concerné
        self.assertEqual(ops.services["crm"]["state"], ONLINE)

        # sales bloqué…
        vs = gov.submit(Action(type=ActionType.EXTERNAL_SENSITIVE, actor="sales_agent",
                               sensitive=True), AutonomyLevel.A5)
        self.assertEqual(vs.rule, "OPS-SUSPENDED")
        # …mais finance peut toujours opérer (pas de SAFE MODE global) : la garde OPS ne le bloque pas
        vf = gov.submit(Action(type=ActionType.EXTERNAL_SENSITIVE, actor="finance_agent",
                               sensitive=True, validated=True), AutonomyLevel.A2)
        self.assertNotIn(vf.rule, ("OPS-SUSPENDED", "OPS-SAFE"))


class TestReturnRequiresExplicitHandover(unittest.TestCase):
    def test_no_silent_resume(self) -> None:
        # invariant 4 : on ne repasse pas en AI_FIRST sans appeler return_to_ai (relecture)
        ops = _ops()
        ops.take_over("emeric", "je reprends la main")
        self.assertEqual(ops.mode, "MANUAL_OVERRIDE")
        self.assertNotEqual(ops.mode, AI_FIRST)               # pas de retour automatique
        ops.return_to_ai("emeric", "terminé")
        self.assertEqual(ops.mode, AI_FIRST)

    def test_readiness_flags_all_true(self) -> None:
        ops = _ops()
        rd = ops.readiness()
        self.assertTrue(all(rd["manual_override"].values()))
        self.assertTrue(all(rd["safe_mode"].values()))


if __name__ == "__main__":
    unittest.main()
