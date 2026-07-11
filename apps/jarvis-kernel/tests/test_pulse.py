"""Tests du Pouls (RFC-0012). Aucun réseau, aucune boucle de fond : tick() direct.

Vérités à protéger :
1. Le Pouls OBSERVE et n'agit jamais — il n'écrit rien dans l'audit de gouvernance.
2. Le briefing dit la vérité : les validations en attente remontent, les tâches
   humaines remontent, et quand il n'y a rien il dit que le silence = tout fonctionne.
3. Un veilleur qui casse (réseau, connecteur) ne tue jamais le battement.
"""

from __future__ import annotations

import unittest

from jarvis_kernel.business.portfolio import seed_known_businesses
from jarvis_kernel.context import build_default_context
from jarvis_kernel.governance.autonomy import AutonomyLevel
from jarvis_kernel.governance.policy import Action, ActionType
from jarvis_kernel.pulse import Pulse


def _ctx():
    ctx = build_default_context()
    # hermétique : on retire le connecteur marché (sinon le veilleur lirait le réseau)
    ctx.connectors = [c for c in ctx.connectors if c.name != "market"]
    return ctx


class TestPulse(unittest.TestCase):
    def test_briefing_mentions_pending_validation(self) -> None:
        ctx = _ctx()
        ctx.governance.submit(Action(type=ActionType.FINANCIAL, actor="test",
                                     description="payer le fournisseur X"), AutonomyLevel.A5)
        text = ctx.pulse.briefing()
        self.assertIn("validation", text)
        self.assertIn("fournisseur X", text)

    def test_briefing_mentions_human_tasks(self) -> None:
        ctx = _ctx()
        seed_known_businesses(ctx.portfolio)
        text = ctx.pulse.briefing()
        self.assertIn("t'attendent", text)

    def test_silence_means_everything_works(self) -> None:
        ctx = _ctx()
        # pas de validation en attente, pas de tâche, connecteurs vidés
        ctx.connectors = []
        self.assertIn("silence signifie que tout fonctionne", ctx.pulse.briefing())

    def test_pulse_never_writes_to_governance_audit(self) -> None:
        ctx = _ctx()
        seed_known_businesses(ctx.portfolio)
        before = len(ctx.governance.audit)
        ctx.pulse.tick()
        ctx.pulse.tick()
        self.assertEqual(len(ctx.governance.audit), before)   # observer ≠ agir

    def test_new_items_emit_bus_events_only_once(self) -> None:
        ctx = _ctx()
        seed_known_businesses(ctx.portfolio)
        ctx.pulse.tick()
        n1 = sum(1 for e in ctx.bus.history if e.name.startswith("pulse."))
        ctx.pulse.tick()                                       # rien de nouveau
        n2 = sum(1 for e in ctx.bus.history if e.name.startswith("pulse."))
        self.assertGreater(n1, 0)
        self.assertEqual(n1, n2)                               # pas de bruit répété

    def test_broken_watcher_does_not_kill_tick(self) -> None:
        ctx = _ctx()

        def boom():
            raise RuntimeError("veilleur cassé")

        ctx.pulse._watch_tasks = boom
        items = ctx.pulse.tick()                               # ne lève pas
        self.assertIsInstance(items, list)

    def test_start_stop_idempotent(self) -> None:
        ctx = _ctx()
        ctx.pulse.start(interval_s=0)                          # 0 = désactivé
        self.assertIsNone(ctx.pulse._thread)
        ctx.pulse.start(interval_s=3600)
        ctx.pulse.start(interval_s=3600)                       # 2e appel : no-op
        ctx.pulse.stop()
        self.assertIsNone(ctx.pulse._thread)

    def test_pulse_restarts_after_stop(self) -> None:
        # régression : l'Event _stop doit être réarmé, sinon Pouls mort-né au redémarrage
        ctx = _ctx()
        ctx.pulse.start(interval_s=3600)
        ctx.pulse.stop()
        ctx.pulse.start(interval_s=3600)
        self.assertIsNotNone(ctx.pulse._thread)
        self.assertTrue(ctx.pulse._thread.is_alive())
        ctx.pulse.stop()

    def test_validation_count_decays_after_resolution(self) -> None:
        # régression : l'audit est append-only — une demande validée ensuite (allow
        # sur la même description) ne doit plus compter comme « en attente »
        ctx = _ctx()
        desc = "payer le fournisseur Y"
        ctx.governance.submit(Action(type=ActionType.FINANCIAL, actor="test",
                                     description=desc), AutonomyLevel.A5)
        self.assertIn("attendent ta validation", ctx.pulse.briefing())
        ctx.governance.submit(Action(type=ActionType.FINANCIAL, actor="test",
                                     description=desc, validated=True), AutonomyLevel.A5)
        self.assertNotIn("attendent ta validation", ctx.pulse.briefing())

    def test_failed_watcher_is_reported_not_silenced(self) -> None:
        # régression « fausse sérénité » : veilleur en échec ≠ « tout fonctionne »
        ctx = _ctx()
        ctx.connectors = []

        def boom():
            raise RuntimeError("réseau coupé")

        ctx.pulse._watch_tasks = boom
        text = ctx.pulse.briefing()
        self.assertNotIn("tout fonctionne", text)
        self.assertIn("information partielle", text)


class TestConversationMemory(unittest.TestCase):
    def test_jarvis_remembers_exchanges(self) -> None:
        ctx = build_default_context()
        ctx.jarvis.handle("bonjour HELYOS")
        ctx.jarvis.handle("où en sont mes business ?")
        hist = ctx.jarvis.history()
        self.assertEqual(len(hist), 4)                         # 2 échanges = 4 entrées
        self.assertEqual(hist[0]["role"], "fondateur")
        self.assertEqual(hist[1]["role"], "helyos")
        self.assertEqual(hist[3]["intent"], "portefeuille")

    def test_thread_is_capped(self) -> None:
        ctx = build_default_context()
        for i in range(30):
            ctx.jarvis.handle(f"message {i}")
        self.assertLessEqual(len(ctx.jarvis.history()), ctx.jarvis._THREAD_MAX)


if __name__ == "__main__":
    unittest.main()
