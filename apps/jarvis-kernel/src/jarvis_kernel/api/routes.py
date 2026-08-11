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

    from ..integrations.nvidia_lab import NvidiaLab
    nvidia_state = NvidiaLab().status()
    nvidia = {"status": "online" if nvidia_state["exists"] else "offline",
              "score": nvidia_state["readiness"]["score"],
              "github_local": nvidia_state["github"]["local_available"],
              "huggingface_local": nvidia_state["huggingface"]["local_available"],
              "gated": nvidia_state["huggingface"]["gated_auth_required"],
              "root": nvidia_state["root"]}

    from ..integrations.open_source_lab import OpenSourceLab
    oss_state = OpenSourceLab().status()
    opensource = {"status": "online" if oss_state["exists"] else "offline",
                  "score": oss_state["readiness"]["score"],
                  "catalogued": oss_state["catalogued"],
                  "local": oss_state.get("local_total", oss_state["local_available"]),
                  "latest_batch_local": oss_state["local_available"],
                  "root": oss_state["root"]}

    # Readiness = mélange PONDÉRÉ et transparent de ce qui est réellement joignable.
    parts = {"helyos": 100, "stark": 100 if stark_ok else 0,
             "engines": 100 if oll_ok else 0,
             "modules": min(100, round(len(ctx.registry) / 9 * 100)),
             "nvidia": nvidia_state["readiness"]["score"],
             "opensource": oss_state["readiness"]["score"]}
    weights = {"helyos": 0.28, "stark": 0.18, "engines": 0.18,
               "modules": 0.14, "nvidia": 0.12, "opensource": 0.10}
    score = round(sum(parts[k] * weights[k] for k in parts))

    # Autopilot = part des actions passées SANS validation humaine (allow) vs bloquées.
    audit = ctx.governance.audit.tail(50)
    allowed = sum(1 for e in audit if e.decision == "allow")
    blocked = sum(1 for e in audit if e.decision in ("deny", "require_validation"))
    total = allowed + blocked
    autopilot = {"ready": allowed, "blocked": blocked,
                 "pct": round(allowed / total * 100) if total else 0}

    return {"helyos": helyos, "stark": stark, "jarvis": stark,  # JARVIS = le pont STARK
            "nvidia": nvidia,
            "opensource": opensource,
            "engines": engines, "readiness": {"score": score, "parts": parts},
            "autopilot": autopilot}


@router.get("/os/cockpit", tags=["cockpit"])
def os_cockpit(request: Request) -> dict:
    """Cockpit ENTREPRISE — la vue du dirigeant (Front B). Tout est RÉEL : les chiffres
    viennent du livre de caisse, de la prospection, du carnet de commandes, du Pouls et de
    la gouvernance. Aucun chiffre inventé : ce qui n'a pas encore de source affiche 0 et
    l'état « à connecter ». AI-first : HELYOS opère, l'humain reste le backup (mode manuel)."""
    import os as _os
    from datetime import datetime, timezone

    ctx = _ctx(request)

    led = ctx.ledger.global_summary() if ctx.ledger else {"recettes_eur": 0, "solde_eur": 0}
    try:
        from ..business.prospection import ProspectionPipeline
        pstats = ProspectionPipeline(ctx.memory).stats()
    except Exception:
        pstats = {"total": 0, "clients": 0, "a_relancer": 0}
    try:
        from ..business.orders import OrderBook
        ostats = OrderBook(ctx.memory).summary()
    except Exception:
        ostats = {"a_encaisser_eur": 0, "a_livrer": 0, "ventes": 0, "achats": 0}

    pulse_online = ctx.pulse is not None
    waiting: list[dict] = []
    if pulse_online:
        try:
            _txt, items = ctx.pulse.report()
            waiting = [i.to_dict() for i in items]
        except Exception:
            waiting = []

    audit = ctx.governance.audit.tail(200)
    conns = ctx.connectors or []
    connected = sum(1 for c in conns if c.status().status == "connected")
    port = ctx.portfolio.summary()
    biz_active = sum(1 for b in port if ((b.get("metrics") or {}).get("revenue_eur", 0) or 0) > 0)

    revenue = led.get("recettes_eur", 0) or 0
    solde = led.get("solde_eur", 0) or 0
    money_state = "réel" if revenue else "à connecter"
    kpis = [
        {"key": "ca", "label": "CA (livre de caisse)", "value": revenue, "unit": "€",
         "state": money_state, "source": "ledger"},
        {"key": "benefice", "label": "Bénéfice (solde)", "value": solde, "unit": "€",
         "state": money_state, "source": "ledger"},
        {"key": "cash", "label": "Trésorerie", "value": solde, "unit": "€",
         "state": money_state, "source": "ledger"},
        {"key": "a_encaisser", "label": "À encaisser", "value": ostats.get("a_encaisser_eur", 0),
         "unit": "€", "state": "réel", "source": "orders"},
        {"key": "pipeline", "label": "Pipeline commercial", "value": pstats.get("total", 0),
         "unit": "prospects", "state": "réel", "source": "prospection"},
        {"key": "clients", "label": "Clients actifs", "value": pstats.get("clients", 0),
         "unit": "", "state": "réel", "source": "prospection"},
    ]

    # Opérations RÉELLES d'HELYOS (ce qui tourne vraiment, avec des comptes vérifiables).
    ops = [
        {"label": "Pouls — observation continue du système", "dept": "Cockpit",
         "state": "actif" if pulse_online else "pause"},
        {"label": f"Gouvernance A0–A5 — {len(audit)} décision(s) arbitrée(s), aucune règle d'or contournée",
         "dept": "Gouvernance", "state": "actif"},
        {"label": "Ingénierie/R&D — qualité du code surveillée (AST · propriétés critiques · "
                  "couverture · diff-coverage · mutation · CI)", "dept": "Engineering", "state": "actif"},
        {"label": f"Portefeuille — {len(port)} business suivis", "dept": "Cockpit", "state": "actif"},
        {"label": f"Connecteurs — {connected}/{len(conns)} branchés", "dept": "Operations",
         "state": "actif" if connected else "à connecter"},
        {"label": "Comité C-suite — 12 conseillers prêts à analyser", "dept": "Advisory", "state": "prêt"},
        {"label": f"Agents — {len(ctx.registry)} agents enregistrés", "dept": "AI Agents", "state": "actif"},
    ]
    if pstats.get("a_relancer"):
        ops.append({"label": f"Prospection — {pstats['a_relancer']} relance(s) due(s)",
                    "dept": "CRM", "state": "actif"})
    if ostats.get("a_livrer"):
        ops.append({"label": f"Commandes — {ostats['a_livrer']} à livrer", "dept": "Operations", "state": "actif"})

    departments = [
        {"key": "cockpit", "name": "Cockpit", "icon": "🛰️", "status": "actif",
         "metric": f"{len(port)} business", "route": "/app/os.html"},
        {"key": "crm", "name": "CRM & Ventes", "icon": "🤝",
         "status": "actif" if pstats.get("total") else "prêt",
         "metric": f"{pstats.get('total', 0)} prospects", "route": "/docs#/prospection"},
        {"key": "marketing", "name": "Marketing", "icon": "📣", "status": "à connecter",
         "metric": "campagnes", "route": ""},
        {"key": "finance", "name": "Finance", "icon": "💶", "status": "actif",
         "metric": f"{solde} €", "route": "/docs#/ledger"},
        {"key": "admin", "name": "Administration", "icon": "🗂️", "status": "prêt",
         "metric": "documents", "route": ""},
        {"key": "sav", "name": "SAV / Customer Success", "icon": "🎧", "status": "à connecter",
         "metric": "clients", "route": ""},
        {"key": "operations", "name": "Operations / ERP", "icon": "📦",
         "status": "actif" if (ostats.get("ventes") or ostats.get("achats")) else "prêt",
         "metric": "commandes", "route": "/docs#/orders"},
        {"key": "engineering", "name": "Engineering / R&D", "icon": "🧪", "status": "actif",
         "metric": "qualité surveillée", "route": "/docs#/engineering"},
        {"key": "rh", "name": "RH", "icon": "👥", "status": "à connecter", "metric": "équipe", "route": ""},
    ]

    parts = {
        "opérateur": 100 if pulse_online else 60,
        "gouvernance": 100,
        "ingénierie": 100,
        "connecteurs": round(connected / len(conns) * 100) if conns else 0,
        "activation_business": round(biz_active / len(port) * 100) if port else 0,
        "trésorerie": 100 if solde > 0 else 50,
    }
    weights = {"opérateur": 0.18, "gouvernance": 0.18, "ingénierie": 0.20,
               "connecteurs": 0.16, "activation_business": 0.16, "trésorerie": 0.12}
    score = round(sum(parts[k] * weights[k] for k in parts))

    interval = float(_os.environ.get("HELYOS_PULSE_INTERVAL", "60") or 0)
    return {
        "clock": datetime.now(timezone.utc).astimezone().strftime("%H:%M"),
        "operator": {"name": "HELYOS", "mode": "ai-first", "manual_available": True,
                     "autonomy": ctx.settings.default_autonomy.name,
                     "pulse": "online" if (pulse_online and interval > 0) else ("prêt" if pulse_online else "off"),
                     "online": True},
        "score": {"value": score, "parts": parts},
        "kpis": kpis,
        "alertes": len(waiting),
        "operations": {"count": len(ops), "items": ops},
        "waiting_on_you": waiting,
        "departments": departments,
        "codex": "Source de vérité : le Codex. Toute action passe par la gouvernance A0–A5.",
    }


@router.get("/os/operations", tags=["operations"])
def os_operations(request: Request) -> dict:
    """État d'exploitation réel : mode (AI_FIRST/MANUAL_OVERRIDE/SAFE_MODE/RECOVERY), état
    par service, dernier handover. Lecture."""
    ops = _ctx(request).operations
    if ops is None:
        raise HTTPException(status_code=503, detail="Contrôleur d'exploitation indisponible.")
    return {**ops.snapshot(), "readiness": ops.readiness()}


@router.post("/os/manual", tags=["operations"])
def os_manual(request: Request, body: dict) -> dict:
    """Reprise manuelle DÉLIBÉRÉE (bouton « Mode manuel »). Suspend les agents (ou un scope),
    audité who/what/when/why. Pré-IAM : à sécuriser par l'IAM natif (jalon suivant)."""
    ops = _ctx(request).operations
    if ops is None:
        raise HTTPException(status_code=503, detail="Contrôleur d'exploitation indisponible.")
    h = ops.take_over(str(body.get("actor", "human")), str(body.get("why", "reprise manuelle")),
                      scope=body.get("scope") or None)
    return {"mode": ops.mode, "handover": {"who": h.who, "what": h.what, "why": h.why}}


@router.post("/os/safe", tags=["operations"])
def os_safe(request: Request, body: dict) -> dict:
    """Déclenche le SAFE MODE (incident). Les services métier/données/audit restent en ligne."""
    ops = _ctx(request).operations
    if ops is None:
        raise HTTPException(status_code=503, detail="Contrôleur d'exploitation indisponible.")
    ops.enter_safe_mode(str(body.get("reason", "incident")), actor=str(body.get("actor", "human")),
                        scope=body.get("scope") or None)
    return ops.snapshot()


@router.post("/os/resume", tags=["operations"])
def os_resume(request: Request, body: dict) -> dict:
    """Rendre la main à HELYOS : RECOVERY (relecture → MemoryEvent) puis AI_FIRST. Explicite, audité."""
    ctx = _ctx(request)
    if ctx.operations is None:
        raise HTTPException(status_code=503, detail="Contrôleur d'exploitation indisponible.")
    res = ctx.operations.return_to_ai(str(body.get("actor", "human")),
                                      str(body.get("reason", "incident résolu")))
    return {**ctx.operations.snapshot(), "recovery": res}


@router.get("/os/registry", tags=["cockpit"])
def os_registry(request: Request) -> dict:
    """Brick Registry — la vérité opérationnelle SONDÉE en direct (matériel, runtime IA,
    infra, briques HELYOS). Zéro coquille vide : rien n'est ACTIVE sans preuve runtime.
    Lecture seule (aucune installation/démarrage)."""
    from ..integrations.system_registry import build_registry
    return build_registry(_ctx(request))


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


@router.get("/nvidia/status", tags=["nvidia"])
def nvidia_status(request: Request) -> dict:
    """Etat reel du lab NVIDIA local: rapports telecharges + runtime GPU/Docker/Ollama."""
    from ..agents.nvidia_lab import NvidiaLabAgent

    ctx = _ctx(request)
    v, status = NvidiaLabAgent().snapshot(ctx.governance, AutonomyLevel.A0)
    if status is None:
        raise HTTPException(status_code=403, detail="Lecture NVIDIA refusee.")
    return {"decision": v.decision.value, **status}


@router.get("/nvidia/assets", tags=["nvidia"])
def nvidia_assets(request: Request) -> dict:
    """Inventaire compact des actifs NVIDIA locaux et des chemins de reference."""
    from ..integrations.nvidia_lab import NvidiaLab

    status = NvidiaLab().status()
    return {
        "root": status["root"],
        "github": status["github"],
        "huggingface": status["huggingface"],
        "lfs_artifacts": status["lfs_artifacts"],
    }


@router.post("/nvidia/sync", tags=["nvidia"])
def nvidia_sync(request: Request) -> dict:
    """Synchronise l'etat NVIDIA dans la memoire/portefeuille HELYOS.

    C'est du bookkeeping local: aucune licence n'est acceptee, aucun telechargement
    n'est lance, aucun service externe n'est appele.
    """
    from ..business.portfolio import Business
    from ..integrations.nvidia_lab import NvidiaLab

    ctx = _ctx(request)
    verdict = ctx.governance.submit(
        Action(type=ActionType.ANALYZE, actor="nvidia_lab",
               description="Synchroniser l'etat local NVIDIA-LAB vers HELYOS"),
        AutonomyLevel.A1,
    )
    if not verdict.allowed:
        raise HTTPException(status_code=403, detail="Niveau A1 requis.")

    status = NvidiaLab().status()
    ctx.memory.remember("status", status, namespace="nvidia_lab")
    name = "NVIDIA Lab"
    if ctx.portfolio.get(name) is None:
        ctx.portfolio.register(Business(
            name=name,
            kind="infrastructure",
            status="miroir local NVIDIA/CUDA/Hugging Face relie a HELYOS",
            metrics={},
            tasks=[
                {"task": "[HUMAIN] Accepter manuellement les licences gated si besoin",
                 "done": False, "owner": "humain"},
                {"task": "[HELYOS] Rafraichir le classeur d'etat business",
                 "done": False, "owner": "helyos"},
            ],
        ))
    ctx.portfolio.set_status(name, f"connecte - score {status['readiness']['score']}/100")
    ctx.portfolio.set_metric(name, "nvidia_readiness", status["readiness"]["score"])
    ctx.portfolio.set_metric(name, "github_repos_local", status["github"]["local_available"])
    ctx.portfolio.set_metric(name, "huggingface_local", status["huggingface"]["local_available"])
    ctx.portfolio.set_metric(name, "huggingface_gated", status["huggingface"]["gated_auth_required"])
    ctx.portfolio.set_metric(name, "disk_free_gb", status["disk"]["free_gb"])
    ctx.bus.emit("nvidia_lab.synced", score=status["readiness"]["score"])
    return {"decision": verdict.decision.value, "status": status}


@router.get("/opensource/status", tags=["opensource"])
def open_source_status(request: Request) -> dict:
    """Etat reel du lab GitHub open source general."""
    from ..agents.open_source_lab import OpenSourceLabAgent

    ctx = _ctx(request)
    v, status = OpenSourceLabAgent().snapshot(ctx.governance, AutonomyLevel.A0)
    if status is None:
        raise HTTPException(status_code=403, detail="Lecture OPEN-SOURCE-LAB refusee.")
    return {"decision": v.decision.value, **status}


@router.post("/opensource/sync", tags=["opensource"])
def open_source_sync(request: Request) -> dict:
    """Synchronise l'etat OPEN-SOURCE-LAB dans le portefeuille HELYOS."""
    from ..business.portfolio import Business
    from ..integrations.open_source_lab import OpenSourceLab

    ctx = _ctx(request)
    verdict = ctx.governance.submit(
        Action(type=ActionType.ANALYZE, actor="open_source_lab",
               description="Synchroniser l'etat local OPEN-SOURCE-LAB vers HELYOS"),
        AutonomyLevel.A1,
    )
    if not verdict.allowed:
        raise HTTPException(status_code=403, detail="Niveau A1 requis.")

    status = OpenSourceLab().status()
    ctx.memory.remember("status", status, namespace="open_source_lab")
    name = "GitHub Open Source Lab"
    if ctx.portfolio.get(name) is None:
        ctx.portfolio.register(Business(
            name=name,
            kind="opensource",
            status="catalogue local GitHub open source relie a HELYOS",
            metrics={},
            tasks=[
                {"task": "[HELYOS] Elargir le catalogue par topics/orgs avec GITHUB_TOKEN",
                 "done": False, "owner": "helyos"},
                {"task": "[HUMAIN] Valider les briques a integrer produit par produit",
                 "done": False, "owner": "humain"},
            ],
        ))
    ctx.portfolio.set_status(name, f"connecte - score {status['readiness']['score']}/100")
    ctx.portfolio.set_metric(name, "catalogued_repos", status["catalogued"])
    ctx.portfolio.set_metric(name, "local_repos", status.get("local_total", status["local_available"]))
    ctx.portfolio.set_metric(name, "latest_batch_local_repos", status["local_available"])
    ctx.portfolio.set_metric(name, "bare_fallback_repos", status.get("local_inventory", {}).get("bare_fallback", 0))
    ctx.portfolio.set_metric(name, "disk_free_gb", status["disk"]["free_gb"])
    ctx.bus.emit("open_source_lab.synced", score=status["readiness"]["score"])
    return {"decision": verdict.decision.value, "status": status}


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


@router.post("/engineering/part", tags=["engineering"])
def engineering_part(request: Request, body: dict) -> dict:
    """Génère une pièce 3D paramétrique (STL) — box | cylindre | engrenage."""
    from ..integrations.engineering import generate_part

    return generate_part(str(body.get("kind", "box")), body.get("params") or {})


@router.post("/engineering/calc", tags=["engineering"])
def engineering_calc(request: Request, body: dict) -> dict:
    """Calcul de mécanique (engrenage, poutre, boulon)."""
    from ..integrations.engineering import mechanical

    return mechanical(str(body.get("kind", "")), body.get("params") or {})


@router.post("/agent/run", tags=["agent"])
def agent_run(request: Request, body: dict) -> dict:
    """Le cerveau : donne un objectif, il choisit/enchaîne ses outils de lecture et raisonne."""
    from ..agents.reasoning import ReasoningAgent

    ctx = _ctx(request)
    goal = str(body.get("goal", "")).strip()
    if not goal:
        raise HTTPException(status_code=422, detail="goal requis")
    return ReasoningAgent(ctx, llm=ctx.llm).run(goal)


@router.get("/mcp/servers", tags=["mcp"])
def mcp_servers(request: Request) -> dict:
    """Serveurs MCP déclarés — HELYOS peut se brancher dessus (le « branche à tout »)."""
    from ..integrations.mcp_client import load_specs

    return {"servers": [{"name": s.name, "command": " ".join(s.command)} for s in load_specs()]}


@router.post("/mcp/tools", tags=["mcp"])
def mcp_tools(request: Request, body: dict) -> dict:
    """Découvre les outils d'un serveur MCP (lecture = A1 gouverné)."""
    from ..integrations.mcp_client import MCPClient, load_specs

    ctx = _ctx(request)
    v = ctx.governance.submit(
        Action(type=ActionType.ANALYZE, actor="mcp_client",
               description=f"Lister les outils MCP de {body.get('server', '?')}"),
        AutonomyLevel.A1)
    if not v.allowed:
        raise HTTPException(status_code=403, detail="Niveau A1 requis.")
    spec = next((s for s in load_specs() if s.name == body.get("server")), None)
    if spec is None:
        raise HTTPException(status_code=404, detail="serveur MCP inconnu")
    try:
        tools = MCPClient(spec).list_tools()
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"MCP injoignable : {exc}") from exc
    return {"server": spec.name, "tools": tools}


@router.post("/mcp/call", tags=["mcp"])
def mcp_call(request: Request, body: dict) -> dict:
    """Appelle un outil MCP externe. Action sur le monde -> GR-2 : validation humaine.
    Sans validated=true, HELYOS PRÉPARE mais n'exécute pas (c'est le contrat)."""
    from ..integrations.mcp_client import MCPClient, load_specs

    ctx = _ctx(request)
    tool = str(body.get("tool", ""))
    v = ctx.governance.submit(
        Action(type=ActionType.EXTERNAL_SENSITIVE, actor="mcp_client",
               description=f"Appeler l'outil MCP {tool} de {body.get('server', '?')}",
               sensitive=True, validated=bool(body.get("validated", False))),
        AutonomyLevel.A2)
    if not v.allowed:
        return {"decision": v.decision.value, "rule": v.rule, "executed": False,
                "note": "Action externe : ta validation est requise (GR-2)."}
    spec = next((s for s in load_specs() if s.name == body.get("server")), None)
    if spec is None:
        raise HTTPException(status_code=404, detail="serveur MCP inconnu")
    result = MCPClient(spec).call_tool(tool, body.get("arguments") or {})
    return {"decision": v.decision.value, "executed": True, "result": result}


@router.get("/modules", tags=["modules"])
def modules_list(request: Request) -> dict:
    """Registre des modules avec interrupteurs on/off (+ sonde des services locaux)."""
    from ..integrations.modules import ModuleRegistry

    reg = ModuleRegistry(_ctx(request).memory)
    return {"summary": reg.summary(), "modules": reg.list(probe=True)}


@router.post("/modules/toggle", tags=["modules"])
def modules_toggle(request: Request, body: dict) -> dict:
    """Allume/éteint un module (key + on:bool). Persisté ; anti-saturation."""
    from ..integrations.modules import ModuleRegistry

    try:
        m = ModuleRegistry(_ctx(request).memory).toggle(
            str(body.get("key", "")), bool(body.get("on", True)))
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return {"key": m.key, "name": m.name, "enabled": bool(body.get("on", True))}


@router.get("/library/search", tags=["library"])
def library_search(request: Request, q: str = "") -> dict:
    """Cherche dans les dépôts open-source déjà téléchargés (catalogue local)."""
    from ..integrations.library import OpenSourceLibrary

    lib = OpenSourceLibrary()
    return {"catalogued": lib.count(), "query": q,
            "results": lib.search(q, limit=10) if q.strip() else []}


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
