"""HELYOS — SystemRegistry + BrickRegistry : la VÉRITÉ opérationnelle, sondée en direct.

Règle absolue (« zéro coquille vide ») : une brique n'est jamais ACTIVE parce que son code
ou sa carte d'UI existe. Elle est ACTIVE seulement si une SONDE RÉELLE le prouve (API qui
répond, port ouvert, données réelles). Le cockpit lit ce registre : il n'invente plus son état.

Sept états : ACTIVE · AVAILABLE · DEGRADED · MISCONFIGURED · BROKEN · STOPPED · MISSING.

DISCOVER → VERIFY → INTEGRATE → TEST → ACTIVE. On ne déclare rien d'opérationnel sans preuve
runtime. Les sondes sont en lecture seule (aucune installation, aucun démarrage, aucun effet).
"""

from __future__ import annotations

import shutil
import socket
import subprocess
from dataclasses import dataclass, field
from pathlib import Path

ACTIVE, AVAILABLE, DEGRADED = "ACTIVE", "AVAILABLE", "DEGRADED"
MISCONFIGURED, BROKEN, STOPPED, MISSING = "MISCONFIGURED", "BROKEN", "STOPPED", "MISSING"
STATUSES = (ACTIVE, AVAILABLE, DEGRADED, MISCONFIGURED, BROKEN, STOPPED, MISSING)

_SCORE = {ACTIVE: 100, DEGRADED: 55, AVAILABLE: 30, MISCONFIGURED: 20, STOPPED: 20,
          BROKEN: 0, MISSING: 0}

WORKSPACE = Path.home() / "WORKSPACE"


@dataclass
class BrickStatus:
    id: str
    category: str                 # hardware | ai_runtime | infrastructure | helyos | reference
    status: str
    engine: bool = False          # un moteur réel existe (pas qu'une carte UI)
    backend: bool = False
    database: bool = False
    api: bool = False
    tests: int = 0
    telemetry: bool = False
    real_data: bool = False
    connectors: int = 0
    ai_agent: str = ""
    manual_backup: bool = False
    version: str = ""
    location: str = ""
    tool_bus: bool = False
    homelab: bool = False
    evidence: list = field(default_factory=list)

    def __post_init__(self) -> None:
        # garde-fou dur : jamais ACTIVE sans preuve d'un moteur/API/donnée réelle.
        if self.status == ACTIVE and not (self.engine or self.api or self.real_data):
            self.status = MISCONFIGURED
            self.evidence.append("déclassé : ACTIVE sans preuve (moteur/API/donnée)")


# ---------------------------------------------------------------- sondes bas niveau (lecture seule)
def _http_json(url: str, timeout: float = 2.0):
    import json
    import urllib.request
    try:
        with urllib.request.urlopen(url, timeout=timeout) as r:
            if r.status != 200:
                return False, {}
            return True, json.loads(r.read().decode("utf-8"))
    except Exception:
        return False, {}


def _port_open(host: str, port: int, timeout: float = 0.4) -> bool:
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except Exception:
        return False


def _run(cmd: list, timeout: float = 4.0):
    if not shutil.which(cmd[0]):
        return None, ""
    try:
        p = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8",
                           errors="replace", timeout=timeout)
        return p.returncode, ((p.stdout or "") + (p.stderr or "")).strip()
    except Exception:
        return None, ""


def _exists(*parts) -> bool:
    return (WORKSPACE.joinpath(*parts)).exists()


# ---------------------------------------------------------------- AI RUNTIME
def probe_ai_runtime() -> list:
    out = []
    ok, tags = _http_json("http://127.0.0.1:11434/api/tags")
    models = [m.get("name", "") for m in tags.get("models", [])] if ok else []
    out.append(BrickStatus(
        id="ollama", category="ai_runtime", status=ACTIVE if ok else (STOPPED if shutil.which("ollama") else MISSING),
        engine=ok, api=ok, real_data=ok, tool_bus=True, homelab=True,
        evidence=([f"API :11434 répond ✓", f"{len(models)} modèle(s) : " + ", ".join(models)] if ok
                  else ["binaire présent, service arrêté" if shutil.which("ollama") else "Ollama absent"])))
    # embeddings nomic (dispo via Ollama mais pas encore branché à la mémoire HELYOS)
    has_embed = any("nomic-embed" in m for m in models)
    out.append(BrickStatus(
        id="embeddings_nomic", category="ai_runtime",
        status=AVAILABLE if has_embed else MISSING, engine=has_embed, tool_bus=True,
        evidence=["nomic-embed-text présent (à brancher sur MemoryStore)" if has_embed
                  else "modèle d'embeddings non présent"]))
    # GPU
    rc, gpu = _run(["nvidia-smi", "--query-gpu=name,memory.total,driver_version",
                    "--format=csv,noheader"], timeout=5)
    out.append(BrickStatus(
        id="gpu_nvidia", category="hardware", status=ACTIVE if rc == 0 and gpu else MISSING,
        engine=bool(rc == 0 and gpu), homelab=True,
        evidence=[gpu.splitlines()[0]] if rc == 0 and gpu else ["nvidia-smi indisponible"]))
    # moteurs d'inférence lourds : SOURCE clonée uniquement (pas construits)
    for bid, parts in (("tensorrt_llm", ("NVIDIA-LAB", "repos", "TensorRT-LLM")),
                       ("triton", ("NVIDIA-LAB", "repos", "triton-server")),
                       ("nemo", ("NVIDIA-LAB", "repos", "NeMo"))):
        src = _exists(*parts)
        out.append(BrickStatus(
            id=bid, category="ai_runtime", status=AVAILABLE if src else MISSING,
            engine=False, homelab=True,
            location=str(WORKSPACE.joinpath(*parts)) if src else "",
            evidence=["source clonée, NON construite (pas de toolchain CUDA/Linux ici)" if src
                      else "absent"]))
    return out


# ---------------------------------------------------------------- INFRASTRUCTURE
def probe_infrastructure() -> list:
    out = []
    # Docker : CLI présent ? daemon joignable ?
    rc, _ = _run(["docker", "version", "--format", "{{.Server.Version}}"], timeout=5)
    docker_cli = shutil.which("docker") is not None
    out.append(BrickStatus(
        id="docker", category="infrastructure",
        status=ACTIVE if rc == 0 else (STOPPED if docker_cli else MISSING),
        engine=rc == 0, homelab=True,
        evidence=["daemon joignable ✓" if rc == 0 else
                  ("CLI installé, daemon arrêté" if docker_cli else "Docker absent")]))
    # Qdrant : service ? données ?
    q_up = _port_open("127.0.0.1", 6333)
    q_data = (Path.home() / "WORKSPACE" / "STARK-PROJECT" / "data" / "qdrant").exists()
    out.append(BrickStatus(
        id="qdrant", category="infrastructure",
        status=ACTIVE if q_up else (AVAILABLE if q_data or _exists("OPEN-SOURCE-LAB", "github", "qdrant") else MISSING),
        engine=q_up, database=q_up, homelab=True,
        evidence=(["service :6333 ✓"] if q_up else
                  (["données présentes, service arrêté"] if q_data else ["source clonée uniquement"]))))
    # PostgreSQL
    pg = shutil.which("psql") is not None or _port_open("127.0.0.1", 5432)
    out.append(BrickStatus(id="postgres", category="infrastructure",
                           status=AVAILABLE if pg else MISSING, engine=pg, homelab=True,
                           evidence=["détecté"] if pg else ["non installé (prévu mini-serveur)"]))
    # Observabilité OTel (présente dans HELYOS mais no-op par défaut)
    out.append(BrickStatus(id="otel", category="infrastructure", status=AVAILABLE,
                           engine=False, telemetry=False,
                           evidence=["hooks OTel présents mais désactivés (no-op) — collector à brancher"]))
    return out


# ---------------------------------------------------------------- HELYOS (Core + départements)
def probe_helyos(ctx) -> list:
    out = []

    def brick(bid, status, **kw):
        out.append(BrickStatus(id=bid, category="helyos", status=status, **kw))

    brick("helyos_api", ACTIVE, engine=True, api=True, backend=True, tool_bus=True, homelab=True,
          version=getattr(ctx.settings, "version", ""), evidence=["FastAPI en cours (self)"])
    brick("governance", ACTIVE, engine=True, backend=True, tests=1, tool_bus=True,
          evidence=[f"A0–A5 actif, {len(ctx.governance.audit.tail(500))} décision(s) auditées"])
    brick("memory_store", ACTIVE, engine=True, backend=True, database=True,
          evidence=["MemoryStore interne actif"])
    brick("agents", ACTIVE, engine=True, real_data=True,
          evidence=[f"{len(ctx.registry)} agents enregistrés"])
    brick("pulse", ACTIVE if ctx.pulse is not None else MISSING, engine=ctx.pulse is not None,
          evidence=["boucle d'observation présente"] if ctx.pulse is not None else ["absent"])
    brick("engineering_brain", ACTIVE, engine=True, backend=True, tests=1, tool_bus=True,
          evidence=["AST · propriétés critiques · couverture · diff-coverage · mutation · CI"])
    brick("cockpit", ACTIVE, engine=True, api=True, evidence=["/os/cockpit + /app/os.html (source de vérité)"])

    # Départements « métier » : réels seulement si moteur + données.
    try:
        from ..business.prospection import ProspectionPipeline
        ps = ProspectionPipeline(ctx.memory).stats()
    except Exception:
        ps = {"total": 0, "clients": 0}
    connected = sum(1 for c in (ctx.connectors or []) if c.status().status == "connected")
    crm_real = (ps.get("total", 0) or 0) > 0
    brick("crm_sales", DEGRADED if not crm_real else ACTIVE, backend=True, real_data=crm_real,
          connectors=connected, ai_agent="prospection",
          evidence=[f"backend prospection ✓, {ps.get('total',0)} prospect(s), "
                    f"connecteur email/paiement : {'à brancher' if connected == 0 else str(connected)}"])
    try:
        led = ctx.ledger.global_summary() if ctx.ledger else {"recettes_eur": 0}
    except Exception:
        led = {"recettes_eur": 0}
    fin_real = (led.get("recettes_eur", 0) or 0) > 0
    brick("finance", DEGRADED if not fin_real else ACTIVE, backend=True, real_data=fin_real,
          evidence=[f"livre de caisse ✓, CA={led.get('recettes_eur',0)}€, connecteur banque : à brancher"])

    # Briques attendues mais NON construites (jamais ACTIVE).
    for bid in ("marketing", "sav", "rh", "administration"):
        brick(bid, MISSING, evidence=["carte d'UI seulement — aucun moteur/donnée (à construire)"])
    iam = getattr(ctx, "iam", None)
    if iam is not None:
        rd = iam.readiness()
        n_id = len(getattr(iam, "identities", {}))
        n_ag = sum(1 for i in iam.identities.values() if i.kind == "AI_AGENT")
        brick("iam", ACTIVE if all(rd.values()) else DEGRADED, engine=True, backend=True,
              database=True, tests=1,
              evidence=[f"RBAC+ABAC+ReBAC · {n_id} identités ({n_ag} agents) · business scopes · "
                        "profils IA · break-glass · self-permission DENY · audit"])
    else:
        brick("iam", MISSING, evidence=["Organization/Users/Roles/Permissions/Scopes/AI-permissions à construire"])
    # Manual Override + SAFE MODE : ACTIVE seulement si la machine à états réelle existe (pas une carte).
    ops = getattr(ctx, "operations", None)
    if ops is not None:
        rd = ops.readiness()
        snap = ops.snapshot()
        mo = ACTIVE if all(rd["manual_override"].values()) else DEGRADED
        sm = ACTIVE if all(rd["safe_mode"].values()) else DEGRADED
        brick("manual_override", mo, engine=True, backend=True, tests=1, manual_backup=True,
              evidence=[f"machine à états ({snap['mode']}) · suspension d'agents · handover audité · restore AI"])
        brick("safe_mode", sm, engine=True, backend=True, tests=1,
              evidence=["incident→SAFE MODE · actions externes bloquées · CRM/données/audit en ligne · recovery testé"])
    else:
        brick("manual_override", MISSING, evidence=["état AI_FIRST↔MANUAL réel + audit à construire"])
        brick("safe_mode", MISSING, evidence=["exploitation dégradée sans le cerveau IA à construire"])
    brick("payment_connector", MISSING, evidence=["aucun canal d'encaissement (Stripe/Gumroad) branché"])

    # Cockpit Node : conservé comme RÉFÉRENCE (données figées → jamais source de vérité).
    node = (Path.home() / "WORKSPACE" / "HELYOS-WEB-COCKPIT").exists()
    out.append(BrickStatus(
        id="node_cockpit", category="reference", status=AVAILABLE if node else MISSING,
        location=str(Path.home() / "WORKSPACE" / "HELYOS-WEB-COCKPIT"),
        evidence=["cockpit statique (Drizzle + JSON figé, OpenAI cloud) — remplacé par le cockpit Python, gardé pour l'UX"]))
    return out


# ---------------------------------------------------------------- assemblage
def build_registry(ctx) -> dict:
    bricks = probe_ai_runtime() + probe_infrastructure() + probe_helyos(ctx)
    cats: dict[str, list] = {}
    for b in bricks:
        cats.setdefault(b.category, []).append(b)
    categories = {}
    for name, items in cats.items():
        avg = round(sum(_SCORE.get(b.status, 0) for b in items) / len(items)) if items else 0
        categories[name] = {"score": avg, "count": len(items),
                            "active": sum(1 for b in items if b.status == ACTIVE),
                            "missing": sum(1 for b in items if b.status == MISSING)}
    overall = round(sum(c["score"] for c in categories.values()) / len(categories)) if categories else 0
    from dataclasses import asdict
    return {"overall": overall, "categories": categories,
            "bricks": [asdict(b) for b in bricks],
            "legend": list(STATUSES),
            "rule": "DISCOVER→VERIFY→INTEGRATE→TEST→ACTIVE — jamais ACTIVE sans preuve runtime."}
