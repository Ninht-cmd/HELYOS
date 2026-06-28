"""Routes de l'API du Kernel (FastAPI).

Surface minimale (RFC-0001) :
- GET  /health              état du Kernel
- GET  /agents              agents enregistrés
- GET  /governance/levels   l'échelle A0–A5
- GET  /governance/audit    journal d'audit récent
- POST /intent              soumettre une intention -> verdict de gouvernance
- GET  /events              historique récent du bus
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request

from ..context import KernelContext
from ..governance.autonomy import AutonomyLevel
from ..governance.policy import Action, ActionType
from .schemas import (
    AgentInfo,
    AuditEntryResponse,
    HealthResponse,
    IntentRequest,
    LevelInfo,
    VerdictResponse,
)

router = APIRouter()


def _ctx(request: Request) -> KernelContext:
    return request.app.state.kernel


@router.get("/health", response_model=HealthResponse, tags=["kernel"])
def health(request: Request) -> HealthResponse:
    cfg = _ctx(request).settings
    return HealthResponse(status="ok", app=cfg.app_name, version=cfg.version)


@router.get("/agents", response_model=list[AgentInfo], tags=["agents"])
def list_agents(request: Request) -> list[AgentInfo]:
    return [AgentInfo(**a.describe()) for a in _ctx(request).registry.list()]


@router.get("/governance/levels", response_model=list[LevelInfo], tags=["governance"])
def levels() -> list[LevelInfo]:
    return [LevelInfo(level=lv.name, rank=int(lv), label=lv.label) for lv in AutonomyLevel]


@router.get("/governance/audit", response_model=list[AuditEntryResponse], tags=["governance"])
def audit(request: Request, limit: int = 20) -> list[AuditEntryResponse]:
    entries = _ctx(request).governance.audit.tail(limit)
    return [AuditEntryResponse(**e.to_dict()) for e in entries]


@router.post("/intent", response_model=VerdictResponse, tags=["governance"])
def submit_intent(request: Request, body: IntentRequest) -> VerdictResponse:
    ctx = _ctx(request)

    try:
        action_type = ActionType(body.action_type)
    except ValueError:
        valid = ", ".join(t.value for t in ActionType)
        raise HTTPException(
            status_code=400,
            detail=f"action_type invalide : {body.action_type!r}. Valeurs : {valid}",
        )

    granted = (
        AutonomyLevel.from_name(body.granted_level)
        if body.granted_level
        else ctx.settings.default_autonomy
    )

    action = Action(
        type=action_type,
        description=body.description,
        target=body.target,
        actor=body.actor,
        has_backup=body.has_backup,
        sensitive=body.sensitive,
        reversible=body.reversible,
        validated=body.validated,
    )

    verdict = ctx.governance.submit(action, granted)
    return VerdictResponse(
        decision=verdict.decision.value,
        reason=verdict.reason,
        rule=verdict.rule,
        required_level=verdict.required_level.name,
        granted_level=verdict.granted_level.name,
        allowed=verdict.allowed,
    )


@router.get("/events", tags=["kernel"])
def events(request: Request, limit: int = 50) -> list[dict]:
    history = _ctx(request).bus.history[-limit:]
    return [{"name": e.name, "ts": e.ts, "payload": e.payload} for e in history]
