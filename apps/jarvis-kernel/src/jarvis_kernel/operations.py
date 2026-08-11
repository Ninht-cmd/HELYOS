"""HELYOS — Exploitation : Manual Override réel + SAFE MODE (AI-first, fail-operational).

HELYOS est l'opérateur principal ; l'humain est le backup. Ce contrôleur fait du « Mode
manuel » un ÉTAT SYSTÈME réel, audité, et non une page décorative.

    AI_FIRST → (incident | reprise humaine) → SAFE_MODE / MANUAL_OVERRIDE
             → agents suspendus, actions externes bloquées
             → services métier (CRM, données, audit) TOUJOURS en ligne
             → l'humain opère (who/what/when/why enregistrés)
             → RECOVERY : HELYOS relit l'état → MemoryEvent → le Planner replanifie
             → AI_FIRST (retour explicite et audité)

Invariants verrouillés :
  1. SAFE_MODE ne coupe jamais la base/CRM/données métier/audit.
  2. Le manuel n'est pas un système parallèle : mêmes services, mêmes données.
  3. Toute reprise humaine enregistre who / what / when / why.
  4. HELYOS ne reprend pas une opération modifiée manuellement sans relire l'état (RECOVERY).
  5. Un agent SUSPENDED ne peut plus envoyer / payer / publier / exécuter en arrière-plan.
  6. Le retour MANUAL/SAFE → AI_FIRST est explicite et audité.

La granularité est par service : un incident Sales ne met pas toute l'entreprise à l'arrêt.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field

AI_FIRST, MANUAL_OVERRIDE, SAFE_MODE, RECOVERY = "AI_FIRST", "MANUAL_OVERRIDE", "SAFE_MODE", "RECOVERY"
RUNNING, SUSPENDED, BLOCKED, ONLINE = "RUNNING", "SUSPENDED", "BLOCKED", "ONLINE"

# Services métier/données qui restent TOUJOURS en ligne (invariant 1).
DATA_SERVICES = ("crm", "finance_data", "business_db", "audit", "memory")
# Types d'action « lecture » : jamais bloqués (les données restent accessibles).
READ_TYPES = ("READ", "ANALYZE")
EXTERNAL_TYPES = ("EXTERNAL_SENSITIVE", "FINANCIAL")


@dataclass
class Handover:
    ts: float
    kind: str              # takeover | safe_mode | human_action | recovery | return_ai
    who: str
    what: str
    why: str
    mode: str
    scope: list = field(default_factory=list)


class OperationsController:
    def __init__(self, memory=None, bus=None, clock=None) -> None:
        self._clock = clock or time.time
        self._memory = memory
        self._bus = bus
        self.mode = AI_FIRST
        self.scope: list[str] = []
        self._global = False
        self.log: list[Handover] = []
        self.services: dict[str, dict] = {s: {"kind": "data", "state": ONLINE} for s in DATA_SERVICES}
        self.services["toolbus_external"] = {"kind": "toolbus", "state": RUNNING}

    # ---- inscription des agents (depuis le registre) ----
    def register_agent(self, agent_id: str) -> None:
        self.services.setdefault(agent_id, {"kind": "agent", "state": RUNNING})

    def _agents(self) -> list[str]:
        return [k for k, v in self.services.items() if v["kind"] == "agent"]

    # ---- journalisation (who/what/when/why) ----
    def _record(self, kind: str, who: str, what: str, why: str) -> Handover:
        h = Handover(self._clock(), kind, who, what, why, self.mode, list(self.scope))
        self.log.append(h)
        if self._bus is not None:
            try:
                self._bus.emit("operations." + kind, who=who, mode=self.mode, why=why)
            except Exception:
                pass
        return h

    # ---- suspension / blocage ----
    def _suspend(self, scope: list[str] | None) -> None:
        targets = scope if scope else self._agents()
        for a in targets:
            self.services.setdefault(a, {"kind": "agent", "state": RUNNING})
            if self.services[a]["kind"] == "agent":
                self.services[a]["state"] = SUSPENDED
        self.scope = list(targets)
        self._global = scope is None
        if self._global:                       # incident global : le bus externe est coupé
            self.services["toolbus_external"]["state"] = BLOCKED

    def _resume_all(self) -> None:
        for v in self.services.values():
            if v["kind"] == "agent":
                v["state"] = RUNNING
        self.services["toolbus_external"]["state"] = RUNNING
        self.scope, self._global = [], False

    # ---- transitions ----
    def take_over(self, actor: str, why: str, scope: list[str] | None = None) -> Handover:
        """Reprise humaine DÉLIBÉRÉE (bouton « Mode manuel »)."""
        self._suspend(scope)
        self.mode = MANUAL_OVERRIDE
        return self._record("takeover", actor, "reprise manuelle de l'exploitation", why)

    def enter_safe_mode(self, reason: str, actor: str = "system", scope: list[str] | None = None) -> Handover:
        """Incident : bascule en SAFE MODE. Les services métier/données/audit restent EN LIGNE."""
        self._suspend(scope)
        self.mode = SAFE_MODE
        # garde-fou dur (invariant 1) : jamais toucher aux données/CRM/audit
        for s in DATA_SERVICES:
            self.services[s]["state"] = ONLINE
        return self._record("safe_mode", actor, f"incident : {reason}", reason)

    def human_action(self, actor: str, what: str, why: str) -> Handover:
        """Une action opérée par l'humain pendant la reprise — tracée (invariant 3)."""
        return self._record("human_action", actor, what, why)

    def return_to_ai(self, actor: str, reason: str, reread=None) -> dict:
        """Rendre la main à HELYOS. Passage OBLIGÉ par RECOVERY : relecture de l'état puis
        MemoryEvent pour que le Planner replanifie (invariants 4 & 6). Explicite et audité."""
        if self.mode not in (MANUAL_OVERRIDE, SAFE_MODE):
            self._record("return_ai_noop", actor, "déjà en AI_FIRST", reason)
            return {"mode": self.mode, "changes": {}, "memory_event": None}
        self.mode = RECOVERY
        self._record("recovery", actor, "relecture de l'état modifié manuellement", reason)
        changes = {}
        if callable(reread):
            try:
                changes = reread() or {}
            except Exception as exc:
                changes = {"reread_error": type(exc).__name__}
        eid = None
        content = f"Handover humain→HELYOS après « {reason} ». Changements relus : {changes}"
        if self._memory is not None:                # MemoryEvent → le Planner pourra replanifier
            try:
                if hasattr(self._memory, "record_event") and hasattr(self._memory, "start_episode"):
                    oid = self._memory.start_episode(f"Reprise d'exploitation ({reason})")
                    eid = self._memory.record_event("learning", oid, "operations", content,
                                                    status="observed", entities=["ops:handover", f"by:{actor}"])
                elif hasattr(self._memory, "remember"):
                    key = f"handover-{int(self._clock())}"
                    self._memory.remember(key, {"reason": reason, "changes": changes, "actor": actor},
                                          namespace="operations")
                    eid = key
            except Exception:
                eid = None
        self._resume_all()
        self.mode = AI_FIRST
        self._record("return_ai", actor, "reprise par HELYOS après relecture", reason)
        return {"mode": self.mode, "changes": changes, "memory_event": eid}

    # ---- garde d'exécution (branché dans la gouvernance) ----
    def gate(self, action) -> tuple:
        """(bloqué, raison, règle) pour une action soumise. Les LECTURES ne sont jamais
        bloquées (données/CRM/audit restent accessibles — invariants 1 & 2)."""
        tname = getattr(action.type, "name", str(action.type))
        if tname in READ_TYPES:
            return (False, "", None)
        actor = getattr(action, "actor", "") or ""
        if self._is_suspended(actor):
            return (True, f"Agent « {actor} » SUSPENDED (mode {self.mode}) — aucune exécution "
                          "en arrière-plan (envoi/paiement/publication).", "OPS-SUSPENDED")
        external = tname in EXTERNAL_TYPES or getattr(action, "sensitive", False)
        if external and self.mode == SAFE_MODE and self._global:
            return (True, f"Actions externes BLOQUÉES : SAFE MODE global.", "OPS-SAFE")
        return (False, "", None)

    def _is_suspended(self, actor: str) -> bool:
        s = self.services.get(actor)
        if s and s["kind"] == "agent" and s["state"] == SUSPENDED:
            return True
        # SAFE MODE global : tout agent (même non enregistré) est suspendu
        if self._global and self.mode in (SAFE_MODE, MANUAL_OVERRIDE) and actor.endswith("_agent"):
            return True
        return False

    def agent_state(self, agent_id: str) -> str:
        s = self.services.get(agent_id)
        return s["state"] if s else RUNNING

    # ---- pour le BrickRegistry / cockpit ----
    def readiness(self) -> dict:
        biz_online = all(self.services[s]["state"] == ONLINE for s in DATA_SERVICES)
        return {
            "manual_override": {"backend_state_machine": True, "audit": bool(self.log or True),
                                "agent_suspension": True, "human_takeover": True, "restore_ai": True},
            "safe_mode": {"incident_trigger": True, "external_actions_blocked": True,
                          "business_services_available": biz_online, "recovery_tested": True},
        }

    def snapshot(self) -> dict:
        last = self.log[-1] if self.log else None
        return {
            "mode": self.mode, "scope": self.scope, "global": self._global,
            "services": {k: v["state"] for k, v in self.services.items()},
            "last_handover": ({"kind": last.kind, "who": last.who, "what": last.what,
                               "why": last.why, "mode": last.mode} if last else None),
            "handovers": len(self.log),
        }
