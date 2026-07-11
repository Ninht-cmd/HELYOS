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
    BriefingResponse,
    BusinessDetail,
    ConnectorStatusResponse,
    HealthResponse,
    HistoryEntry,
    IntentRequest,
    JarvisReplyResponse,
    JarvisRequest,
    LevelInfo,
    PortfolioItem,
    SyncResultResponse,
    TaskCompleteRequest,
    VerdictResponse,
)

router = APIRouter()


def _ctx(request: Request) -> KernelContext:
    return request.app.state.kernel


def _parse_level(raw: str | None, default: AutonomyLevel) -> AutonomyLevel:
    """A0..A5 (ou 0..5) -> niveau. Valeur inconnue = 400, pas une rétrogradation silencieuse."""
    if raw is None:
        return default
    key = raw.strip().upper().removeprefix("A")
    if not (key.isdigit() and 0 <= int(key) <= 5):
        raise HTTPException(status_code=400,
                            detail=f"granted_level invalide : {raw!r}. Valeurs : A0..A5.")
    return AutonomyLevel(int(key))


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
    entries = _ctx(request).governance.audit.tail(max(1, min(limit, 500)))
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

    granted = _parse_level(body.granted_level, ctx.settings.default_autonomy)

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
    history = _ctx(request).bus.history[-max(1, min(limit, 500)):]
    return [{"name": e.name, "ts": e.ts, "payload": e.payload} for e in history]


@router.post("/jarvis", response_model=JarvisReplyResponse, tags=["jarvis"])
def talk_to_jarvis(request: Request, body: JarvisRequest) -> JarvisReplyResponse:
    """Point d'entrée unifié : langage naturel -> intention -> action gouvernée -> réponse."""
    ctx = _ctx(request)
    if ctx.jarvis is None:
        raise HTTPException(status_code=503, detail="Jarvis non initialisé.")

    granted = _parse_level(body.granted_level, ctx.settings.default_autonomy)
    reply = ctx.jarvis.handle(body.message, granted=granted)
    return JarvisReplyResponse(
        intent=reply.intent,
        text=reply.text,
        governed=reply.governed,
        decision=reply.decision,
        rule=reply.rule,
    )


@router.get("/portfolio", response_model=list[PortfolioItem], tags=["business"])
def portfolio(request: Request) -> list[PortfolioItem]:
    """État réel du portefeuille de business — la source est la mémoire du Kernel."""
    return [PortfolioItem(**b) for b in _ctx(request).portfolio.summary()]


@router.get("/portfolio/detail", response_model=list[BusinessDetail], tags=["business"])
def portfolio_detail(request: Request) -> list[BusinessDetail]:
    """Portefeuille avec les tâches — alimente le poste de pilotage."""
    ctx = _ctx(request)
    return [
        BusinessDetail(name=b.name, kind=b.kind, status=b.status, metrics=b.metrics,
                       open_tasks=b.open_tasks, tasks=b.tasks)
        for b in ctx.portfolio.list()
    ]


@router.get("/pulse/briefing", response_model=BriefingResponse, tags=["pulse"])
def pulse_briefing(request: Request) -> BriefingResponse:
    """Le briefing proactif : validations en attente, tâches humaines, marché, connecteurs.
    S'il n'y a rien, il le dit — le silence signifie que tout fonctionne."""
    pulse = _ctx(request).pulse
    if pulse is None:
        raise HTTPException(status_code=503, detail="Pouls indisponible.")
    text, items = pulse.report()             # UN battement : texte et items cohérents
    return BriefingResponse(text=text, items=[i.to_dict() for i in items])


@router.get("/jarvis/history", response_model=list[HistoryEntry], tags=["jarvis"])
def jarvis_history(request: Request) -> list[HistoryEntry]:
    """Le fil de conversation mémorisé — un Jarvis se souvient."""
    jarvis = _ctx(request).jarvis
    if jarvis is None:
        raise HTTPException(status_code=503, detail="Jarvis non initialisé.")
    return [HistoryEntry(**e) for e in jarvis.history()]


@router.get("/prospection", tags=["prospection"])
def prospection(request: Request) -> dict:
    """Pipeline de prospection réel : prospects, statuts, relances dues, stats vendredi."""
    from ..business.prospection import ProspectionPipeline

    pipe = ProspectionPipeline(_ctx(request).memory)
    return {"stats": pipe.stats(),
            "due": [{"name": p.name, "next": nxt} for p, nxt in pipe.due_followups()],
            "prospects": [p.to_dict() for p in pipe.list()]}


@router.post("/prospection", tags=["prospection"])
def prospection_add(request: Request, body: dict) -> dict:
    """Ajoute un prospect (name requis) et rend un brouillon de premier contact."""
    from ..business.prospection import ProspectionPipeline

    name = str(body.get("name", "")).strip()
    if not name:
        raise HTTPException(status_code=422, detail="name requis")
    ctx = _ctx(request)
    pipe = ProspectionPipeline(ctx.memory)
    p = pipe.add(name, company=str(body.get("company", "")),
                 contact=str(body.get("contact", "")), note=str(body.get("note", "")))
    return {"prospect": p.to_dict(), "draft": pipe.draft_outreach(ctx.llm, p)}


@router.post("/prospection/status", tags=["prospection"])
def prospection_status(request: Request, body: dict) -> dict:
    """Change le statut d'un prospect (contacte, relance_1, repondu, rdv, client, perdu…)."""
    from ..business.prospection import ProspectionPipeline

    try:
        p = ProspectionPipeline(_ctx(request).memory).set_status(
            str(body.get("name", "")), str(body.get("status", "")))
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return p.to_dict()


@router.get("/paper", tags=["paper"])
def paper_summary(request: Request) -> dict:
    """Portefeuille de trading SIMULÉ (argent fictif) — toujours étiqueté comme tel."""
    from ..agents.paper_trader import PaperTrader

    return PaperTrader().summary(_ctx(request).memory)


@router.post("/paper/step", tags=["paper"])
def paper_step(request: Request) -> dict:
    """Un pas de stratégie simulée — gouverné (A1), aucun ordre réel possible."""
    from ..agents.paper_trader import PaperTrader

    ctx = _ctx(request)
    try:
        v, s = PaperTrader().step(ctx.governance, ctx.memory)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Prix indisponibles : {exc}") from exc
    if s is None:
        raise HTTPException(status_code=403, detail="Niveau A1 requis.")
    return {"decision": v.decision.value, **s}


@router.get("/connectors", response_model=list[ConnectorStatusResponse], tags=["connectors"])
def connectors(request: Request) -> list[ConnectorStatusResponse]:
    """La carte honnête : connecté / à connecter (+ quoi fournir) / interdit (+ pourquoi)."""
    return [ConnectorStatusResponse(**c.status().to_dict())
            for c in (_ctx(request).connectors or [])]


@router.post("/connectors/sync", response_model=SyncResultResponse, tags=["connectors"])
def connectors_sync(request: Request) -> SyncResultResponse:
    """Synchronise les métriques réelles (LECTURE seule) — action gouvernée A1."""
    ctx = _ctx(request)
    verdict = ctx.governance.submit(
        Action(type=ActionType.ANALYZE, actor="connectors",
               description="Synchroniser les connecteurs (lecture seule -> portefeuille)"),
        AutonomyLevel.A1,
    )
    results: list[dict] = []
    if verdict.allowed:
        for c in (ctx.connectors or []):
            if getattr(c, "sync", None) is None:
                continue
            st = c.status()
            if st.status != "connected":
                results.append({"name": c.name, "ok": False, "detail": st.status})
                continue
            try:
                summary = c.sync(ctx.portfolio)
                results.append({"name": c.name, "ok": summary is not None,
                                "detail": summary or {}})
                ctx.bus.emit("connector.synced", connector=c.name)
            except Exception as exc:  # un connecteur qui tombe ne casse pas les autres
                results.append({"name": c.name, "ok": False, "detail": str(exc)[:200]})
    return SyncResultResponse(decision=verdict.decision.value, results=results)


@router.post("/portfolio/complete-task", response_model=BusinessDetail, tags=["business"])
def complete_task(request: Request, body: TaskCompleteRequest) -> BusinessDetail:
    """Coche une tâche (par préfixe). Bookkeeping interne : aucun effet monde,
    donc pas de cérémonie de gouvernance — mais l'événement est tracé sur le bus."""
    ctx = _ctx(request)
    b = ctx.portfolio.complete_task(body.business, body.task_prefix)
    if b is None:
        raise HTTPException(status_code=404, detail=f"Business inconnu : {body.business!r}")
    ctx.bus.emit("portfolio.task_done", business=body.business, task=body.task_prefix)
    return BusinessDetail(name=b.name, kind=b.kind, status=b.status, metrics=b.metrics,
                          open_tasks=b.open_tasks, tasks=b.tasks)
