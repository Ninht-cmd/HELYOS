"""Contexte du Kernel — câble ensemble les composants partagés.

Un seul ``EventBus`` est partagé entre la gouvernance et le reste du système.
Réutilisable hors API (tests, scripts) : ne dépend pas de FastAPI.
"""

from __future__ import annotations

from dataclasses import dataclass

from .agents.base import AgentRegistry, ObserverAgent
from .config import Settings, settings as default_settings
from .governance.audit import AuditLog
from .governance.policy import PolicyEngine
from .governance.service import GovernanceService
from .kernel.event_bus import EventBus
from .memory.store import InMemoryMemoryStore, MemoryStore


@dataclass
class KernelContext:
    settings: Settings
    bus: EventBus
    memory: MemoryStore
    registry: AgentRegistry
    governance: GovernanceService


def build_default_context(settings: Settings | None = None) -> KernelContext:
    """Construit un contexte complet, en mémoire, sans service externe."""
    cfg = settings or default_settings
    bus = EventBus()
    governance = GovernanceService(
        engine=PolicyEngine(),
        audit=AuditLog(),
        bus=bus,  # bus partagé : les décisions de gouvernance circulent sur le bus
    )
    registry = AgentRegistry()
    registry.register(ObserverAgent())  # agent d'exemple A0

    return KernelContext(
        settings=cfg,
        bus=bus,
        memory=InMemoryMemoryStore(),
        registry=registry,
        governance=governance,
    )
