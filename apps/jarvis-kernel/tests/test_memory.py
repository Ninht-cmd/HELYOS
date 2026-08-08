"""Tests de la mémoire long terme unifiée + LE critère d'acceptation :
la mémoire doit MODIFIER le comportement futur (un correctif refusé n'est pas re-proposé)."""

from __future__ import annotations

import unittest

from jarvis_kernel.governance.autonomy import AutonomyLevel
from jarvis_kernel.governance.service import GovernanceService
from jarvis_kernel.world.memory_store import UnifiedMemory
from jarvis_kernel.world.planner import default_orchestrator


def _counter():
    t = [0.0]
    def clock():
        t[0] += 1
        return t[0]
    return clock


class TestMemoryCore(unittest.TestCase):
    def test_decision_lifecycle_and_statuses(self) -> None:
        m = UnifiedMemory(clock=_counter())
        oid = m.start_episode("Réduire les coûts de 15%")
        did = m.record_decision(oid, "supply_chain_agent", "FRN-12 recommandé", status="inferred",
                                confidence=0.93, sources=["data/receptions.csv"],
                                governance={"rule": "GR-2", "decision": "require_validation"},
                                entities=["supplier:FRN-07", "supplier:FRN-12"])
        self.assertEqual(m.decisions[did].status, "inferred")     # pas une vérité : une inférence
        m.set_decision_status(did, "validated", "je valide la piste FRN-12")
        self.assertEqual(m.decisions[did].status, "validated")
        m.record_outcome(did, observed=11.8, expected=15.0, note="économie partielle")
        self.assertTrue(m.decisions[did].outcome_id)
        self.assertEqual(m.summary()["by_status"]["validated"], 1)

    def test_retrieve_finds_similar_and_persists(self) -> None:
        m = UnifiedMemory(clock=_counter())
        oid = m.start_episode("Réduire les coûts fournisseurs")
        did = m.record_decision(oid, "supply_chain_agent", "corriger FRN-07")
        m.set_decision_status(did, "rejected", "trop tôt")
        r = m.retrieve("réduis encore les coûts fournisseurs")
        self.assertTrue(r["has_history"])
        self.assertTrue(any(d["status"] == "rejected" for d in r["rejected"]))
        # persistance : from_dict conserve la mémoire ET la recherche vectorielle
        m2 = UnifiedMemory.from_dict(m.to_dict())
        self.assertTrue(m2.retrieve("coûts fournisseurs")["has_history"])


class TestMemoryChangesBehaviour(unittest.TestCase):
    """LE critère : RUN #1 refus -> RUN #2 ne re-propose pas, cherche autre chose."""

    def setUp(self) -> None:
        self.mem = UnifiedMemory(clock=_counter())
        self.orch = default_orchestrator()
        self.gov = GovernanceService()
        self.cands = {"candidates": ["module_A perf", "module_B doc"]}

    def _propose(self, plan):
        return next(s for s in plan["etapes"] if s["kind"] == "propose")

    def test_rejected_fix_not_reproposed(self) -> None:
        # RUN #1 : propose un correctif -> l'humain REFUSE
        r1 = self.orch.run("Analyse HELYOS et propose une amélioration", self.cands,
                           governance=self.gov, granted=AutonomyLevel.A2, memory=self.mem)
        p1 = self._propose(r1)
        self.assertIsNotNone(p1["decision_id"])
        self.assertFalse(r1["memoire"]["has_history"])            # rien en mémoire au 1er run
        self.mem.set_decision_status(p1["decision_id"], "rejected", "trop risqué pour l'instant")
        content1 = self.mem.decisions[p1["decision_id"]].content

        # RUN #2 : la mémoire doit CHANGER le comportement
        r2 = self.orch.run("Analyse encore HELYOS", self.cands,
                           governance=self.gov, granted=AutonomyLevel.A2, memory=self.mem)
        p2 = self._propose(r2)
        self.assertTrue(r2["memoire"]["has_history"])             # il RETROUVE le passé
        self.assertIn("refusé", p2["resultat"])                  # il l'explique
        self.assertNotEqual(self.mem.decisions[p2["decision_id"]].content, content1)  # AUTRE correctif
        self.assertTrue(any(d["status"] == "rejected" for d in r2["memoire"]["rejected"]))


if __name__ == "__main__":
    unittest.main()
