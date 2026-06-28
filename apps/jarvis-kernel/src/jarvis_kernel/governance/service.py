"""Service de gouvernance — orchestre PolicyEngine + AuditLog + EventBus.

C'est le point d'entrée unique pour soumettre une intention au système.
Toute action passe par ici avant exécution (ADR-0003). Le flux :

    évaluer (PolicyEngine) -> journaliser (AuditLog) -> publier (EventBus)

Événements émis :
- ``governance.decided`` (toujours)
- ``action.allowed`` (si ALLOW)
- ``action.pending_validation`` (si REQUIRE_VALIDATION)
- ``action.denied`` (si DENY)
"""

from __future__ import annotations

from ..kernel.event_bus import EventBus
from ..observability.tracing import span
from .audit import AuditEntry, AuditLog
from .autonomy import AutonomyLevel
from .policy import Action, Decision, PolicyEngine, PolicyVerdict


class GovernanceService:
    def __init__(
        self,
        engine: PolicyEngine | None = None,
        audit: AuditLog | None = None,
        bus: EventBus | None = None,
    ) -> None:
        self.engine = engine or PolicyEngine()
        self.audit = audit or AuditLog()
        self.bus = bus or EventBus()

    def submit(self, action: Action, granted: AutonomyLevel) -> PolicyVerdict:
        """Évalue, journalise et publie. Retourne le verdict."""
        with span(
            "governance.submit",
            **{
                "helyos.action_type": action.type.value,
                "helyos.actor": action.actor,
                "helyos.granted_level": granted.name,
            },
        ):
            return self._submit(action, granted)

    def _submit(self, action: Action, granted: AutonomyLevel) -> PolicyVerdict:
        verdict = self.engine.evaluate(action, granted)

        self.audit.append(
            AuditEntry(
                actor=action.actor,
                action_type=action.type.value,
                action_description=action.description or action.target,
                decision=verdict.decision.value,
                reason=verdict.reason,
                rule=verdict.rule,
                required_level=verdict.required_level.name,
                granted_level=verdict.granted_level.name,
            )
        )

        self.bus.emit(
            "governance.decided",
            actor=action.actor,
            action_type=action.type.value,
            decision=verdict.decision.value,
            rule=verdict.rule,
        )

        topic = {
            Decision.ALLOW: "action.allowed",
            Decision.REQUIRE_VALIDATION: "action.pending_validation",
            Decision.DENY: "action.denied",
        }[verdict.decision]
        self.bus.emit(
            topic,
            actor=action.actor,
            action_type=action.type.value,
            description=action.description,
            reason=verdict.reason,
        )

        return verdict
