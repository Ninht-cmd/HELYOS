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
