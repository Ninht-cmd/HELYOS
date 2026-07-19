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


def _probe(url: str, timeout: float = 1.5) -> tuple[bool, dict]:
    """Sonde HTTP côté serveur (évite le CORS navigateur). Rend (ok, json|{})."""
    import json as _json
    import urllib.request

    try:
        with urllib.request.urlopen(url, timeout=timeout) as r:  # noqa: S310 (URL locale de config)
            if r.status != 200:
                return False, {}
            try:
                return True, _json.loads(r.read().decode("utf-8"))
            except Exception:
                return True, {}
    except Exception:
        return False, {}


@router.get("/cockpit/topology", tags=["cockpit"])
def cockpit_topology(request: Request) -> dict:
    """État RÉEL du triptyque HELYOS ⇄ STARK ⇄ JARVIS + moteur LLM (Ollama).

    HELYOS est le hub : il sonde lui-même les autres services (pas le navigateur),
    ce qui contourne le CORS et fait de ce noyau le vrai point de liaison.
    Rien n'est inventé : un service éteint est marqué 'offline', pas 'standby'.
    """
    import os

    ctx = _ctx(request)
    stark_url = os.environ.get("STARK_JARVIS_URL", "http://127.0.0.1:4242")
    ollama_url = os.environ.get("OLLAMA_URL", "http://127.0.0.1:11434")

    # HELYOS : c'est nous — si on répond, on est en ligne.
    helyos = {"status": "online", "version": ctx.settings.version,
              "agents": len(ctx.registry), "decisions": len(ctx.governance.audit)}

    # STARK / JARVIS : le pont FastAPI du module JARVIS (ADR-0011) expose /health.
    stark_ok, stark_data = _probe(stark_url + "/health")
    stark = {"status": "online" if stark_ok else "offline",
             "helyos_link": stark_data.get("helyos", "?") if stark_ok else "—",
             "url": stark_url}

    # Moteur LLM local : Ollama (:11434/api/tags liste les modèles).
    oll_ok, oll_data = _probe(ollama_url + "/api/tags")
    models = len(oll_data.get("models", [])) if oll_ok else 0
    engines = {"status": "online" if oll_ok else "offline", "models": models,
               "backend": ctx.settings.llm_backend}

    # Readiness = mélange PONDÉRÉ et transparent de ce qui est réellement joignable.
    parts = {"helyos": 100, "stark": 100 if stark_ok else 0,
             "engines": 100 if oll_ok else 0,
             "modules": min(100, round(len(ctx.registry) / 7 * 100))}
    weights = {"helyos": 0.35, "stark": 0.25, "engines": 0.25, "modules": 0.15}
    score = round(sum(parts[k] * weights[k] for k in parts))

    # Autopilot = part des actions passées SANS validation humaine (allow) vs bloquées.
    audit = ctx.governance.audit.tail(50)
    allowed = sum(1 for e in audit if e.decision == "allow")
    blocked = sum(1 for e in audit if e.decision in ("deny", "require_validation"))
    total = allowed + blocked
    autopilot = {"ready": allowed, "blocked": blocked,
                 "pct": round(allowed / total * 100) if total else 0}

    return {"helyos": helyos, "stark": stark, "jarvis": stark,  # JARVIS = le pont STARK
            "engines": engines, "readiness": {"score": score, "parts": parts},
            "autopilot": autopilot}


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


@router.get("/advisory/roles", tags=["advisory"])
def advisory_roles(request: Request) -> list[dict]:
    """Les 12 conseillers du Comité (C-suite) — advisory A1, n'exécutent jamais."""
    from ..agents.advisory import ROLES

    return [{"key": r.key, "title": r.title, "lens": r.lens} for r in ROLES.values()]


@router.post("/advisory", tags=["advisory"])
def advisory_ask(request: Request, body: dict) -> dict:
    """Pose une question au Comité (ou à un C-level nommé). Conseil gouverné A1."""
    from ..agents.advisory import AdvisoryBoard

    ctx = _ctx(request)
    q = str(body.get("message", "")).strip()
    if not q:
        raise HTTPException(status_code=422, detail="message requis")
    v, out = AdvisoryBoard(llm=ctx.llm).advise(ctx, ctx.governance, q)
    if out is None:
        raise HTTPException(status_code=403, detail="Niveau A1 requis.")
    return {"decision": v.decision.value, **out}


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


@router.get("/orders", tags=["orders"])
def orders_list(request: Request) -> dict:
    """Carnet de commandes : ventes (à livrer/encaisser) + achats (fournisseurs)."""
    from ..business.orders import OrderBook

    book = OrderBook(_ctx(request).memory)
    return {"summary": book.summary(),
            "orders": [o.to_dict() for o in book.list()]}


@router.post("/orders", tags=["orders"])
def orders_add(request: Request, body: dict) -> dict:
    """Ajoute une commande (sens=vente|achat, partie, objet, montant_eur)."""
    from ..business.orders import OrderBook

    try:
        o = OrderBook(_ctx(request).memory).add(
            str(body.get("sens", "vente")), str(body.get("partie", "")),
            str(body.get("objet", "")), float(body.get("montant_eur", 0)),
            str(body.get("business", "")))
    except (ValueError, TypeError) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return o.to_dict()


@router.post("/orders/status", tags=["orders"])
def orders_status(request: Request, body: dict) -> dict:
    """Change le statut d'une commande (livree, encaissee, payee, annulee…)."""
    from ..business.orders import OrderBook

    try:
        o = OrderBook(_ctx(request).memory).set_statut(
            str(body.get("id", "")), str(body.get("statut", "")))
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return o.to_dict()


@router.get("/ledger", tags=["ledger"])
def ledger_summary(request: Request, business: str | None = None) -> dict:
    """Bilan de caisse réel : global, ou d'un business (`?business=Nom exact`)."""
    ledger = _ctx(request).ledger
    if ledger is None:
        raise HTTPException(status_code=503, detail="Livre de caisse indisponible.")
    if business:
        return {**ledger.summary(business),
                "dernieres_ecritures": [e.to_dict() for e in ledger.entries(business, 10)]}
    return ledger.global_summary()


@router.post("/ledger", tags=["ledger"])
def ledger_add(request: Request, body: dict) -> dict:
    """Note une écriture DÉJÀ réalisée (recette|depense). N'exécute aucun paiement (GR-7)."""
    ctx = _ctx(request)
    if ctx.ledger is None:
        raise HTTPException(status_code=503, detail="Livre de caisse indisponible.")
    try:
        e = ctx.ledger.add(str(body.get("business", "")), str(body.get("kind", "")),
                           float(body.get("amount_eur", 0)), str(body.get("label", "")))
    except (ValueError, TypeError) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    ctx.bus.emit("ledger.entry", business=e.business, kind=e.kind, amount_eur=e.amount_eur)
    return {"entry": e.to_dict(), "summary": ctx.ledger.summary(e.business)}


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
    # draft=false : chargement en masse sans rédaction LLM (le brouillon viendra à la demande)
    draft = pipe.draft_outreach(ctx.llm, p) if body.get("draft", True) else None
    return {"prospect": p.to_dict(), "draft": draft}


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
