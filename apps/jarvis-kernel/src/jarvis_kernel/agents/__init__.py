"""Agents — intelligence composée (ADN 9).

Chaque agent déclare le niveau d'autonomie qu'il requiert et propose des actions
soumises à la gouvernance. Orchestration cible : LangGraph (CODEX/07_TECH).
"""

from .base import Agent, AgentRegistry, ObserverAgent
from .business_scaffolder import BusinessPlan, BusinessScaffolder, ProductIdea
from .invoice_reminder import Invoice, InvoiceReminderAgent, Reminder
from .llm import LLMPort, OllamaLLM, StubLLM
from .orchestrator import Orchestrator, Step, StepResult
from .research import ResearchAgent
from .scribe import ScribeAgent

__all__ = [
    "Agent",
    "AgentRegistry",
    "ObserverAgent",
    "ScribeAgent",
    "ResearchAgent",
    "Orchestrator",
    "Step",
    "StepResult",
    "LLMPort",
    "StubLLM",
    "OllamaLLM",
    "BusinessScaffolder",
    "BusinessPlan",
    "ProductIdea",
    "InvoiceReminderAgent",
    "Invoice",
    "Reminder",
]
