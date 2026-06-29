"""Contexte du Kernel — câble ensemble les composants partagés.

Un seul ``EventBus`` est partagé entre la gouvernance et le reste du système.
La mémoire (backend choisi par la config), le tracing et les agents sont câblés ici.
Réutilisable hors API (tests, scripts) : ne dépend pas de FastAPI.
"""

from __future__ import annotations

from dataclasses import dataclass

from .agents.base import AgentRegistry, ObserverAgent
from .agents.research import ResearchAgent
from .agents.scribe import ScribeAgent
from .config import Settings, settings as default_settings
from .governance.audit import AuditLog
from .governance.policy import PolicyEngine
from .governance.service import GovernanceService
from .kernel.event_bus import EventBus
from .memory import build_memory
from .memory.store import MemoryStore
from .memory.vector import NaiveVectorMemory, VectorMemory
from .observability.tracing import setup_tracing


@dataclass
class KernelContext:
    settings: Settings
    bus: EventBus
    memory: MemoryStore
    vector: VectorMemory
    registry: AgentRegistry
    governance: GovernanceService


def build_default_context(settings: Settings | None = None) -> KernelContext:
    """Construit un contexte complet. Local First : aucun service externe requis."""
    cfg = settings or default_settings

    # Observabilité : tracing optionnel (no-op si désactivé ou OTel absent).
    setup_tracing(
        enabled=cfg.otel_enabled,
        endpoint=cfg.otel_endpoint,
        service_name=cfg.service_name,
    )

    bus = EventBus()
    governance = GovernanceService(
        engine=PolicyEngine(),
        audit=AuditLog(),
        bus=bus,  # bus partagé : les décisions de gouvernance circulent sur le bus
    )

    memory = build_memory(
        cfg.memory_backend, path=cfg.memory_path, dsn=cfg.memory_dsn or None
    )

    registry = AgentRegistry()
    registry.register(ObserverAgent())  # agent d'exemple A0 (perception)
    registry.register(ScribeAgent())    # premier agent utile : rédige des ADR (A2)
    registry.register(ResearchAgent())  # agent d'analyse (A1), à composer

    return KernelContext(
        settings=cfg,
        bus=bus,
        memory=memory,
        vector=NaiveVectorMemory(),
        registry=registry,
        governance=governance,
    )
