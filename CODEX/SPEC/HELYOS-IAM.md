# HELYOS — IAM entreprise v1 (contrôle d'accès unifié : humains + agents + services)

- **Statut** : Accepted · **Date** : 2026-08-11
- **Implémentation** : `iam.py` · `context.py` (câblage) · `integrations/system_registry.py`
  · endpoints `/os/iam`, `/os/iam/authorize`
- **Tests** : `test_iam.py` (12 : les 11 scénarios d'acceptation + persistance)

---

## 1. Le principe

Personne — humain, agent, service ou connecteur — n'agit directement. Toute action passe par
une identité, un périmètre, une permission, une politique, la gouvernance et l'audit.

```
IDENTITÉ → BUSINESS SCOPE → RBAC → ABAC → ReBAC → PROFIL IA → GOUVERNANCE (A0–A5/GR-x) → OPERATIONS → AUDIT
```

Ordre d'application (`enforce`) : **AUTHN → AUTHZ → OPERATIONS → GOVERNANCE → EXECUTION → AUDIT**.
Un agent `SUSPENDED` reste bloqué même avec la bonne permission. **`A5 ≠ super-admin`** : la
permission effective est l'**intersection** identité ∩ profil IA ∩ business ∩ gouvernance ∩
operations.

## 2. Identités de première classe

`HumanIdentity · AgentIdentity · ServiceIdentity · ConnectorIdentity · EmergencyIdentity`. Un
`sales_agent` est une identité au même titre qu'un employé — avec son propre profil de permissions
IA, ce qui empêche un agent marketing de toucher la trésorerie « parce qu'il a techniquement le Tool Bus ».

## 3. RBAC + ABAC + ReBAC + business scopes

- **RBAC** : rôles → permissions (`crm.read`, `finance.transfer`…), liés **par business** (`bindings`).
- **ABAC** : conditions de contexte (business, montant, `resource_owner`, `safe_mode`, autonomie…).
- **ReBAC** : relations (`manages`, `member_of`, `works_for`, `reports_to`) → « Thomas peut modifier
  Prospect #847 » via la relation, pas seulement le rôle.
- **Business scopes** : un employé peut avoir `WRITE` dans Business A et `READ` dans Business B ;
  aucun accès à Business C. Le CEO peut déléguer par business.

## 4. AI Permission Profile (brique spécifique HELYOS)

Par agent : `observe/analyze/propose/prepare` ; `execute` interne / externe **[GR-2]** / financier
**[GR-7]** / destructif **[DENY]** ; `max_autonomy` ; `max_financial_eur` ; `allowed_businesses`.

## 5. Le PDP central + `enforce`

`authorize(subject, action, resource, context) -> AuthorizationDecision(allowed, reason, policy,
subject, resource, business, risk, layers)`. Puis `enforce()` : si l'IAM refuse on s'arrête ; sinon
l'action est mappée en `ActionType` et soumise à `governance.submit` (qui applique la garde
OPERATIONS puis A0–A5/GR-x). Break-glass (`EmergencyGrant`) : droits temporaires, raison
obligatoire, **auto-révocation** à l'expiration. **Self-permission → DENY** : une identité ne
s'accorde jamais plus de droits (aligné GR-3). Audit append-only de chaque décision (RBAC/ABAC/
ReBAC/Ops/Gouvernance → final).

## 6. Les 11 tests d'acceptation — tous verts

```
1  Sales → CRM de son business        ALLOW
2  Sales → payroll                    DENY  (IAM-RBAC)
3  sales_agent → email.prepare        ALLOW
4  sales_agent → bank.transfer        DENY
5  finance_agent A5 → transfert       REQUIRE_VALIDATION (GR-7 ; A5 ne saute pas)
6  agent SUSPENDED (permission OK)    DENY  (OPS-SUSPENDED)
7  takeover employé hors scope        DENY  (IAM-SCOPE)
8  takeover employé autorisé          ALLOW + AuditEvent
9  Business A → records Business B     DENY  (IAM-SCOPE)
10 EmergencyGrant → expiration         accès auto-révoqué
11 IA modifie sa propre permission     DENY  (IAM-SELF)
```

## 7. BrickRegistry (zéro coquille vide)

`iam` ne passe `ACTIVE` que si `readiness()` est vrai (identités persistées, permissions de rôle,
business scopes, identités d'agents, moteur d'autorisation, audit, self-permission refusée, takeover
protégé). Passe de `MISSING` à **`ACTIVE`** ; overall du registre 48 → 52. Endpoints `/os/iam`
(état) et `/os/iam/authorize` (PDP). Persistance : `to_dict/from_dict` testée (roundtrip).

## 8. Portée honnête & suite

- **v1 livré** : RBAC+ABAC+ReBAC, business scopes par binding, profils IA, break-glass, self-perm
  DENY, risque (fonction + seuil ≥76), audit, persistance.
- **v1.1** (honnête) : **SoD** (créateur ≠ validateur) et sessions/appareils/step-up ne sont pas
  encore appliqués ; le **câblage de `enforce()` sur CHAQUE chemin du Tool Bus** (aujourd'hui les
  agents passent par la gouvernance ; l'IAM v1 est prouvé de bout en bout par `enforce`, pas encore
  systématiquement intercalé partout).
- **Front A / CFG interprocédural** prouvera structurellement qu'aucune action externe n'a de
  chemin contournant `IAM → Operations → Governance`.
- **Ensuite** : **CRM/Sales réel**, désormais multi-utilisateur (prospect → scope IAM → qualification
  → gouvernance → envoi → outcome → mémoire).

Voir [[HELYOS-Operations-SafeMode]], [[HELYOS-System-Registry]], [[HELYOS-Critical-Property-AST]].
