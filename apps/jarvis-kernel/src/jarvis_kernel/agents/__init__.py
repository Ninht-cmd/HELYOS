"""Agents — intelligence composée (ADN 9).

Chaque agent déclare le niveau d'autonomie qu'il requiert et propose des actions
soumises à la gouvernance. Orchestration cible : LangGraph (CODEX/07_TECH).
"""

from .base import Agent, AgentRegistry, ObserverAgent

__all__ = ["Agent", "AgentRegistry", "ObserverAgent"]
