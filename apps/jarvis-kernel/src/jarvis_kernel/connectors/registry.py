"""Registre des connecteurs — la carte honnête de ce qui est branché ou non."""

from __future__ import annotations

from ..config import Settings
from .base import Connector, ConnectorStatus, EnvConnector, Transport
from .github import GitHubConnector
from .shopify import ShopifyConnector
from .smtp import SMTPConnector
from .trading import TradingViewConnector


class OllamaConnector(Connector):
    """Le LLM local — « connecté » selon la config du kernel (pas de réseau au status)."""

    name = "ollama"
    kind = "intelligence"

    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def status(self) -> ConnectorStatus:
        if self.settings.llm_backend.lower() == "ollama":
            return ConnectorStatus(self.name, self.kind, "connected",
                                   detail=f"{self.settings.llm_model} · 100 % local, 0 €/requête")
        return ConnectorStatus(self.name, self.kind, "not_configured",
                               detail="le kernel tourne sur StubLLM (déterministe)",
                               requires="HELYOS_LLM_BACKEND=ollama (+ ollama serve)")


def build_connectors(settings: Settings, transport: Transport | None = None) -> list[Connector]:
    """L'ordre = l'ordre d'affichage. Chaque entrée dit la vérité sur son état."""
    return [
        ShopifyConnector(transport=transport),
        GitHubConnector(transport=transport),
        SMTPConnector(),
        OllamaConnector(settings),
        TradingViewConnector(),               # interdit — et il explique pourquoi
        EnvConnector(name="stripe", kind="paiement",
                     env_vars=("HELYOS_STRIPE_KEY",),
                     requires="HELYOS_STRIPE_KEY (lecture seule ; GR-7 : jamais de paiement autonome)",
                     note="encaissement Audit Flash / Packs — lien de paiement d'abord"),
        EnvConnector(name="n8n", kind="workflows",
                     env_vars=("HELYOS_N8N_URL",),
                     requires="HELYOS_N8N_URL (instance auto-hébergée)",
                     note="moteur des livrables clients (Plan Cash) — licence Sustainable Use"),
        EnvConnector(name="nocodb", kind="donnees",
                     env_vars=("HELYOS_NOCODB_URL", "HELYOS_NOCODB_TOKEN"),
                     requires="HELYOS_NOCODB_URL + HELYOS_NOCODB_TOKEN",
                     note="base no-code des factures clients — licence AGPL à vérifier si SaaS"),
        EnvConnector(name="youtube", kind="youtube",
                     env_vars=("HELYOS_YOUTUBE_API_KEY", "HELYOS_YOUTUBE_CHANNEL_ID"),
                     requires="HELYOS_YOUTUBE_API_KEY + HELYOS_YOUTUBE_CHANNEL_ID",
                     note="statistiques réelles de la chaîne faceless"),
    ]


def statuses(connectors: list[Connector]) -> list[ConnectorStatus]:
    return [c.status() for c in connectors]
