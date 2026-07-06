"""Schémas Pydantic de l'API (couche FastAPI)."""

from __future__ import annotations

from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    status: str = "ok"
    app: str
    version: str


class AgentInfo(BaseModel):
    name: str
    description: str
    required_level: str
    required_level_label: str


class IntentRequest(BaseModel):
    """Soumission d'une intention à la gouvernance."""

    action_type: str = Field(
        ...,
        description="read | analyze | write_local | rename_workdir | delete | "
        "external_sensitive | financial | self_permission",
        examples=["delete"],
    )
    description: str = Field("", examples=["Supprimer le rapport obsolète"])
    target: str = Field("", examples=["/data/rapport.csv"])
    actor: str = Field("unknown", examples=["agent.cleanup"])
    granted_level: str | None = Field(
        None,
        description="A0..A5. Si absent, le niveau par défaut du Kernel s'applique.",
        examples=["A1"],
    )
    has_backup: bool = False
    sensitive: bool = False
    reversible: bool = False
    validated: bool = Field(
        False, description="Le Conservateur a explicitement approuvé cette action."
    )


class VerdictResponse(BaseModel):
    decision: str
    reason: str
    rule: str | None = None
    required_level: str
    granted_level: str
    allowed: bool


class AuditEntryResponse(BaseModel):
    id: str
    ts: float
    actor: str
    action_type: str
    action_description: str
    decision: str
    reason: str
    rule: str | None
    required_level: str
    granted_level: str


class LevelInfo(BaseModel):
    level: str
    rank: int
    label: str


class JarvisRequest(BaseModel):
    """Message en langage naturel adressé à HELYOS (point d'entrée unifié)."""

    message: str = Field(..., min_length=1, examples=["où en sont mes business ?"])
    granted_level: str | None = Field(
        None, description="A0..A5 accordé pour ce tour. Défaut : niveau du Kernel.",
        examples=["A1"],
    )


class JarvisReplyResponse(BaseModel):
    intent: str
    text: str
    governed: bool
    decision: str | None = None
    rule: str | None = None


class PortfolioItem(BaseModel):
    """État réel d'un business géré — aucune métrique inventée."""

    name: str
    kind: str
    status: str
    metrics: dict
    open_tasks: int


class BusinessDetail(PortfolioItem):
    """Un business avec ses tâches (pour le poste de pilotage)."""

    tasks: list[dict]


class TaskCompleteRequest(BaseModel):
    """Pointage d'une tâche du portefeuille (bookkeeping interne, aucun effet monde)."""

    business: str = Field(..., min_length=1, examples=["HELYOS Services (automatisation admin)"])
    task_prefix: str = Field(..., min_length=3, examples=["[HUMAIN] Semaine 1"])


class ConnectorStatusResponse(BaseModel):
    """État honnête d'un connecteur : connected | not_configured | forbidden | error."""

    name: str
    kind: str
    status: str
    detail: str = ""
    requires: str = ""


class SyncResultResponse(BaseModel):
    decision: str
    results: list[dict]
