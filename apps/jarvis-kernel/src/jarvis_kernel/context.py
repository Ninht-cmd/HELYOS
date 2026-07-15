"""Contexte du Kernel — câble ensemble les composants partagés.

Un seul ``EventBus`` est partagé entre la gouvernance et le reste du système.
La mémoire (backend choisi par la config), le tracing et les agents sont câblés ici.
Réutilisable hors API (tests, scripts) : ne dépend pas de FastAPI.
"""

from __future__ import annotations

from dataclasses import dataclass

from .agents.base import AgentRegistry, ObserverAgent
from .agents.business_scaffolder import BusinessScaffolder
from .agents.invoice_reminder import InvoiceReminderAgent
from .agents.llm import LLMPort, StubLLM
from .agents.research import ResearchAgent
from .agents.scribe import ScribeAgent
from .business.portfolio import BusinessPortfolio
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
    portfolio: BusinessPortfolio
    ledger: object | None = None  # livre de caisse par business (RFC-0014)
    llm: LLMPort | None = None    # backend LLM partagé (Stub ou Ollama selon la config)
    jarvis: object | None = None  # instance Jarvis (câblée dans build_default_context)
    connectors: list = None       # connecteurs vers le monde réel (RFC-0009), tous gouvernés
    pulse: object | None = None   # le Pouls : observation continue + briefing (RFC-0012)


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

    # Backend LLM des agents : stub déterministe (défaut) ou vrai modèle local (Ollama).
    llm: LLMPort = StubLLM()
    if cfg.llm_backend.lower() == "ollama":
        from .agents.llm import OllamaLLM
        llm = OllamaLLM(model=cfg.llm_model)

    registry = AgentRegistry()
    registry.register(ObserverAgent())          # agent d'exemple A0 (perception)
    registry.register(ScribeAgent())            # premier agent utile : rédige des ADR (A2)
    registry.register(ResearchAgent(llm=llm))   # analyse (A1) — vrai LLM si backend=ollama
    registry.register(BusinessScaffolder(llm=llm))  # scaffolde un business (A1) ; publication = A2 gouvernée
    registry.register(InvoiceReminderAgent(llm=llm))  # HELYOS v1 : relance de factures (A1) ; envoi = A2 gouverné

    from .agents.market_analyst import MarketAnalystAgent
    registry.register(MarketAnalystAgent())  # analyse marché (A1) ; ordre = GR-7, jamais autonome

    from .agents.paper_trader import PaperTrader
    registry.register(PaperTrader())  # trading en SIMULATION (A1) — argent fictif, jamais réel

    ctx = KernelContext(
        settings=cfg,
        bus=bus,
        memory=memory,
        vector=NaiveVectorMemory(),
        registry=registry,
        governance=governance,
        portfolio=BusinessPortfolio(memory),   # HELYOS gère le portefeuille de business
        llm=llm,
    )

    from .business.ledger import Ledger
    ctx.ledger = Ledger(memory, ctx.portfolio)   # le CA affiché = la somme des écritures

    # Import local : jarvis.py importe KernelContext pour ses annotations, donc on
    # câble l'instance après coup pour éviter l'import circulaire au chargement.
    from .jarvis import Jarvis
    ctx.jarvis = Jarvis(ctx, llm)

    from .connectors import build_connectors
    ctx.connectors = build_connectors(cfg)

    from .pulse import Pulse
    ctx.pulse = Pulse(ctx)   # la boucle de fond n'est démarrée que par l'app (main.py)
    return ctx
