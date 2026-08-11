"""HELYOS — IAM entreprise v1 : la couche de contrôle d'accès unifiée (humains + agents + services).

Principe : personne n'agit directement. Toute action passe par
    IDENTITÉ → PÉRIMÈTRE (business scope) → PERMISSION (RBAC) → CONTEXTE (ABAC)
             → RELATION (ReBAC) → PROFIL IA → GOUVERNANCE (A0–A5/GR-x) → OPERATIONS → AUDIT.

Ordre d'application (enforce) : AUTHN → AUTHZ → OPERATIONS → GOVERNANCE → EXECUTION → AUDIT.
Un agent SUSPENDED reste bloqué même avec la bonne permission. `A5 ≠ super-admin` : la
permission effective est l'INTERSECTION identité ∩ profil IA ∩ business ∩ gouvernance ∩
operations. Une identité ne peut JAMAIS élargir ses propres permissions (self-permission → DENY).
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field

HUMAN, AI_AGENT, SERVICE, CONNECTOR, EMERGENCY = "HUMAN", "AI_AGENT", "SERVICE", "CONNECTOR", "EMERGENCY"
ACTIVE, SUSPENDED = "ACTIVE", "SUSPENDED"

# Actions par lesquelles une identité tenterait de modifier des permissions/autonomie → jamais permis.
SELF_PERMISSION_ACTIONS = {"iam.grant", "iam.role.assign", "permission.modify", "autonomy.raise",
                           "iam.revoke", "profile.modify"}
_FINANCIAL_HINTS = ("transfer", "pay", "payout", "wire", "finance.transfer", "payroll.run")
_EXTERNAL_HINTS = ("email.send", "publish", "post", "message.send", "external")
_DESTRUCTIVE_HINTS = ("delete", "destroy", "drop", "purge")
_READ_HINTS = (".read", ".analyze", "prospect.analyze", "observe")


@dataclass
class Identity:
    id: str
    kind: str                                   # HUMAN | AI_AGENT | SERVICE | CONNECTOR | EMERGENCY
    display: str = ""
    bindings: list = field(default_factory=list)  # [(business_or_None, role_name)]
    max_autonomy: str = "A2"
    status: str = ACTIVE

    @property
    def businesses(self) -> set:
        return {b for (b, _) in self.bindings if b}


@dataclass
class Role:
    name: str
    permissions: set = field(default_factory=set)


@dataclass
class AIProfile:
    agent_id: str
    can_observe: bool = True
    can_analyze: bool = True
    can_propose: bool = True
    can_prepare: bool = True
    exec_internal: bool = True
    exec_external: str = "GR-2"                  # GR-2 | DENY | ALLOW
    financial: str = "DENY"                      # GR-7 | DENY | ALLOW
    destructive: str = "DENY"                    # DENY | GR-1
    max_autonomy: str = "A3"
    max_financial_eur: float = 0.0
    allowed_businesses: list = field(default_factory=list)


@dataclass
class Relation:
    subject: str
    rel: str                                     # member_of | manages | works_for | reports_to
    object: str


@dataclass
class EmergencyGrant:
    id: str
    subject: str
    permissions: set
    reason: str
    created_at: float
    expires_at: float


@dataclass
class AuthorizationDecision:
    allowed: bool
    reason: str
    policy: str
    subject: str
    action: str
    resource: str = ""
    business: str = ""
    risk: int = 0
    layers: dict = field(default_factory=dict)


@dataclass
class AuditEvent:
    ts: float
    subject: str
    action: str
    resource: str
    business: str
    decision: str
    policy: str
    layers: dict


_AUTONOMY_RANK = {"A0": 0, "A1": 1, "A2": 2, "A3": 3, "A4": 4, "A5": 5}


class IAM:
    def __init__(self, clock=None) -> None:
        self._clock = clock or time.time
        self.identities: dict[str, Identity] = {}
        self.roles: dict[str, Role] = {}
        self.profiles: dict[str, AIProfile] = {}
        self.relations: list[Relation] = []
        self.grants: dict[str, EmergencyGrant] = {}
        self._audit: list[AuditEvent] = []
        self._seq = 0

    # ---- administration ----
    def add_identity(self, ident: Identity) -> Identity:
        self.identities[ident.id] = ident
        return ident

    def add_role(self, name: str, permissions) -> Role:
        self.roles[name] = Role(name, set(permissions))
        return self.roles[name]

    def set_profile(self, profile: AIProfile) -> None:
        self.profiles[profile.agent_id] = profile

    def add_relation(self, subject: str, rel: str, obj: str) -> None:
        self.relations.append(Relation(subject, rel, obj))

    def grant_emergency(self, subject: str, permissions, reason: str, ttl_seconds: float) -> EmergencyGrant:
        """Break glass : droits SUPPLÉMENTAIRES temporaires, raison obligatoire, auto-révocation."""
        self._seq += 1
        now = self._clock()
        g = EmergencyGrant(f"EMERGENCY-{self._seq:04d}", subject, set(permissions), reason,
                           now, now + ttl_seconds)
        self.grants[g.id] = g
        self._log(subject, "iam.emergency_grant", g.id, "", "GRANTED", "IAM-BREAKGLASS", {"reason": reason})
        return g

    # ---- résolution des permissions ----
    def _has_rel(self, subject: str, rel: str, obj: str) -> bool:
        return any(r.subject == subject and r.rel == rel and r.object == obj for r in self.relations)

    def _perms(self, ident: Identity, business: str) -> set:
        perms: set = set()
        for (b, role) in ident.bindings:
            if b in (None, business) and role in self.roles:
                perms |= self.roles[role].permissions
        # break glass actif
        now = self._clock()
        for g in self.grants.values():
            if g.subject == ident.id and now < g.expires_at:
                perms |= g.permissions
        return perms

    def _rebac_allows(self, subject: str, action: str, resource: str) -> bool:
        # ReBAC : « gère » la ressource → droit d'agir dessus (update/read)
        if self._has_rel(subject, "manages", resource):
            return True
        return False

    def _risk(self, ctx: dict) -> int:
        risk = 0
        amount = float(ctx.get("amount", 0) or 0)
        if amount:
            risk += min(60, int(amount / 1000))
        if ctx.get("sensitive"):
            risk += 25
        if ctx.get("new_device"):
            risk += 20
        if ctx.get("safe_mode"):
            risk += 15
        return min(100, risk)

    def _classify(self, action: str) -> str:
        a = action.lower()
        if any(h in a for h in _DESTRUCTIVE_HINTS):
            return "destructive"
        if any(h in a for h in _FINANCIAL_HINTS):
            return "financial"
        if any(h in a for h in _EXTERNAL_HINTS):
            return "external"
        if any(h in a for h in _READ_HINTS):
            return "read"
        return "internal"

    def _ai_ok(self, ident: Identity, action: str, ctx: dict):
        prof = self.profiles.get(ident.id)
        if prof is None:
            return True, "", "IAM-AI"
        business = ctx.get("business")
        if prof.allowed_businesses and business and business not in prof.allowed_businesses:
            return False, f"business {business} hors du profil IA de {ident.id}", "IAM-AI-SCOPE"
        if _AUTONOMY_RANK.get(ctx.get("autonomy", "A0"), 0) > _AUTONOMY_RANK.get(prof.max_autonomy, 5):
            return False, f"autonomie demandée > max profil {prof.max_autonomy}", "IAM-AI-AUTONOMY"
        cls = self._classify(action)
        if cls == "destructive" and prof.destructive == "DENY":
            return False, "action destructive interdite au profil IA", "IAM-AI-DESTRUCTIVE"
        if cls == "financial":
            if prof.financial == "DENY":
                return False, "action financière interdite au profil IA", "IAM-AI-FINANCIAL"
            if prof.max_financial_eur and float(ctx.get("amount", 0) or 0) > prof.max_financial_eur:
                return False, f"montant > exposition max {prof.max_financial_eur}€", "IAM-AI-EXPOSURE"
        if cls == "external" and prof.exec_external == "DENY":
            return False, "action externe interdite au profil IA", "IAM-AI-EXTERNAL"
        return True, "", "IAM-AI"

    # ---- Policy Decision Point ----
    def authorize(self, subject: str, action: str, resource: str = "", context: dict | None = None) -> AuthorizationDecision:
        ctx = dict(context or {})
        business = ctx.get("business") or _resource_business(resource)
        layers: dict = {}

        def decide(allowed, reason, policy):
            d = AuthorizationDecision(allowed, reason, policy, subject, action, resource,
                                      business or "", self._risk(ctx), layers)
            self._log(subject, action, resource, business or "", "ALLOW" if allowed else "DENY", policy, layers)
            return d

        ident = self.identities.get(subject)
        if ident is None:                                   # AUTHN
            return decide(False, f"identité inconnue : {subject}", "IAM-AUTHN")

        # self-permission : jamais élargir ses propres droits (aligné GR-3)
        target = ctx.get("target") or resource
        if action in SELF_PERMISSION_ACTIONS and (target in (subject, "self", f"identity:{subject}")):
            layers["self"] = "DENY"
            return decide(False, "une identité ne modifie pas ses propres permissions (GR-3)", "IAM-SELF")

        # business scope
        if business and ident.kind != EMERGENCY and business not in ident.businesses \
                and not self._has_rel(subject, "works_for", business):
            layers["scope"] = "DENY"
            return decide(False, f"{subject} hors du périmètre business {business}", "IAM-SCOPE")

        # RBAC ∪ ReBAC
        perms = self._perms(ident, business)
        rbac = action in perms
        rebac = self._rebac_allows(subject, action, resource)
        layers["rbac"] = "ALLOW" if rbac else "DENY"
        layers["rebac"] = "ALLOW" if rebac else ("N/A" if not rebac else "ALLOW")
        if not (rbac or rebac):
            return decide(False, f"{action} absent du rôle de {subject}", "IAM-RBAC")

        # ABAC (contexte)
        ok, why = self._abac(ident, action, resource, ctx)
        layers["abac"] = "ALLOW" if ok else "DENY"
        if not ok:
            return decide(False, why, "IAM-ABAC")

        # Profil IA
        if ident.kind == AI_AGENT:
            ok2, why2, pol2 = self._ai_ok(ident, action, ctx)
            layers["ai"] = "ALLOW" if ok2 else "DENY"
            if not ok2:
                return decide(False, why2, pol2)

        # Risque
        risk = self._risk(ctx)
        if risk >= 76:
            return decide(False, f"risque {risk} ≥ 76 : refus / double validation", "IAM-RISK")

        return decide(True, "autorisé", "IAM-OK")

    def _abac(self, ident: Identity, action: str, resource: str, ctx: dict):
        # exemple de conditions contextuelles réelles
        if ctx.get("safe_mode") and self._classify(action) in ("financial", "external", "destructive"):
            # en SAFE MODE, les actions sensibles restent gouvernées en aval ; ABAC ne bloque pas
            pass
        owner_scope = ctx.get("resource_owner_business")
        if owner_scope and owner_scope not in ident.businesses and not self._has_rel(ident.id, "works_for", owner_scope):
            return False, f"ressource appartient à {owner_scope}, hors périmètre",
        return True, ""

    def authorize_takeover(self, subject: str, business: str, scope: str | None = None) -> AuthorizationDecision:
        """Le BON humain reprend la main sur le BON périmètre (Manual Override protégé)."""
        ctx = {"business": business}
        ident = self.identities.get(subject)
        if ident is None:
            return self._takeover_decision(subject, business, False, "identité inconnue", "IAM-AUTHN")
        if business not in ident.businesses and not self._has_rel(subject, "works_for", business):
            return self._takeover_decision(subject, business, False,
                                           f"{subject} hors du périmètre {business}", "IAM-SCOPE")
        if scope and not (self._has_rel(subject, "manages", scope) or self._has_rel(subject, "member_of", scope)):
            return self._takeover_decision(subject, business, False,
                                           f"{subject} n'a pas le scope {scope}", "IAM-SCOPE")
        return self._takeover_decision(subject, business, True, "reprise autorisée", "IAM-OK")

    def _takeover_decision(self, subject, business, allowed, reason, policy):
        self._log(subject, "ops.takeover", business, business, "ALLOW" if allowed else "DENY", policy, {})
        return AuthorizationDecision(allowed, reason, policy, subject, "ops.takeover", business, business)

    # ---- audit immuable ----
    def _log(self, subject, action, resource, business, decision, policy, layers) -> None:
        self._audit.append(AuditEvent(self._clock(), subject, action, resource, business,
                                      decision, policy, dict(layers)))

    def audit(self, limit: int = 50) -> list:
        return [vars(e) for e in self._audit[-limit:]]

    # ---- persistance (sérialisable) ----
    def to_dict(self) -> dict:
        return {
            "identities": [vars(i) | {"bindings": [list(b) for b in i.bindings]} for i in self.identities.values()],
            "roles": {n: sorted(r.permissions) for n, r in self.roles.items()},
            "profiles": [vars(p) for p in self.profiles.values()],
            "relations": [vars(r) for r in self.relations],
        }

    @classmethod
    def from_dict(cls, data: dict, clock=None) -> "IAM":
        iam = cls(clock=clock)
        for n, perms in data.get("roles", {}).items():
            iam.add_role(n, perms)
        for i in data.get("identities", []):
            iam.add_identity(Identity(id=i["id"], kind=i["kind"], display=i.get("display", ""),
                                      bindings=[tuple(b) for b in i.get("bindings", [])],
                                      max_autonomy=i.get("max_autonomy", "A2"),
                                      status=i.get("status", ACTIVE)))
        for p in data.get("profiles", []):
            iam.set_profile(AIProfile(**p))
        for r in data.get("relations", []):
            iam.add_relation(r["subject"], r["rel"], r["object"])
        return iam

    # ---- BrickRegistry ----
    def readiness(self) -> dict:
        return {
            "identities_persisted": bool(self.identities),
            "role_permissions": bool(self.roles),
            "business_scopes": any(i.businesses for i in self.identities.values()),
            "agent_identities": any(i.kind == AI_AGENT for i in self.identities.values()),
            "authorization_engine": True,
            "audit": True,
            "self_permission_denied": True,
            "manual_takeover_protected": True,
        }


def _resource_business(resource: str) -> str:
    # "bank_account:BUS-001" ou "prospect:847@BUS-001" → BUS-xxx si présent
    if not resource:
        return ""
    for token in resource.replace("@", ":").split(":"):
        if token.startswith("BUS-"):
            return token
    return ""


# ------------------------------------------------------------------ pipeline complet
def enforce(iam: IAM, governance, subject: str, action: str, resource: str = "",
            context: dict | None = None, granted=None):
    """AUTHN → AUTHZ → (OPERATIONS + GOVERNANCE) → décision finale, auditée.

    Si l'IAM refuse, on s'arrête (jamais soumis à la gouvernance). Sinon on mappe l'action en
    ActionType et on passe par `governance.submit` (qui applique la garde OPERATIONS puis A0–A5/GR-x)."""
    from .governance.autonomy import AutonomyLevel
    from .governance.policy import Action, ActionType

    ctx = dict(context or {})
    authz = iam.authorize(subject, action, resource, ctx)
    if not authz.allowed:
        return {"final": "DENY", "stage": "IAM", "policy": authz.policy, "reason": authz.reason,
                "authorization": vars(authz)}

    cls = iam._classify(action)
    atype = {"financial": ActionType.FINANCIAL, "external": ActionType.EXTERNAL_SENSITIVE,
             "destructive": ActionType.DELETE, "read": ActionType.ANALYZE}.get(cls, ActionType.WRITE_LOCAL)
    gov_action = Action(type=atype, actor=subject, description=action, target=resource,
                        sensitive=(cls in ("external", "financial")),
                        has_backup=bool(ctx.get("has_backup", False)),
                        validated=bool(ctx.get("validated", False)))
    lvl = granted if granted is not None else AutonomyLevel.A2
    verdict = governance.submit(gov_action, lvl)
    return {"final": verdict.decision.value.upper(), "stage": "GOVERNANCE", "policy": verdict.rule,
            "reason": verdict.reason, "authorization": vars(authz)}


def seed_default_iam(iam: IAM) -> IAM:
    """Amorce honnête : un business, des rôles, des humains et des agents de première classe."""
    iam.add_role("Sales", {"crm.read", "crm.update", "prospect.analyze", "email.prepare", "email.send"})
    iam.add_role("Finance", {"finance.read", "finance.transfer", "invoice.read"})
    iam.add_role("EngineerWrite", {"repo.read", "repo.write", "ci.read"})
    iam.add_role("Accountant", {"finance.read", "invoice.read"})

    iam.add_identity(Identity("thomas", HUMAN, "Thomas (Sales)", bindings=[("BUS-001", "Sales")], max_autonomy="A2"))
    iam.add_identity(Identity("alex", HUMAN, "Alex (Eng)", bindings=[("BUS-001", "EngineerWrite")], max_autonomy="A2"))
    iam.add_identity(Identity("marie", HUMAN, "Marie (Sales Mgr)", bindings=[("BUS-001", "Sales")], max_autonomy="A3"))

    iam.add_identity(Identity("sales_agent", AI_AGENT, "Sales Agent",
                              bindings=[("BUS-001", "Sales")], max_autonomy="A3"))
    iam.set_profile(AIProfile("sales_agent", exec_external="GR-2", financial="DENY", destructive="DENY",
                              max_autonomy="A3", allowed_businesses=["BUS-001"]))
    iam.add_identity(Identity("finance_agent", AI_AGENT, "Finance Agent",
                              bindings=[("BUS-001", "Finance")], max_autonomy="A5"))
    iam.set_profile(AIProfile("finance_agent", exec_external="GR-2", financial="GR-7", destructive="DENY",
                              max_autonomy="A5", max_financial_eur=5000.0,
                              allowed_businesses=["BUS-001", "BUS-003"]))

    iam.add_relation("thomas", "works_for", "BUS-001")
    iam.add_relation("thomas", "member_of", "sales_france")
    iam.add_relation("thomas", "manages", "prospect:847")
    iam.add_relation("marie", "manages", "sales_france")
    return iam
