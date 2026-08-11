# HELYOS — Manual Override + SAFE MODE (AI-first, fail-operational)

- **Statut** : Accepted · **Date** : 2026-08-11
- **Implémentation** : `operations.py` · `governance/service.py` (garde) · `context.py` (câblage)
  · `integrations/system_registry.py` · endpoints `/os/operations|manual|safe|resume` · cockpit
- **Tests** : `test_operations.py` (4) + `test_system_registry.py` (maj)

---

## 1. Le « Mode manuel » devient un ÉTAT SYSTÈME, pas une page

HELYOS est l'opérateur principal ; l'humain est le backup. `OperationsController` fait du mode
manuel un état réel, audité, avec granularité par service.

Modèle : `AI_FIRST · MANUAL_OVERRIDE · SAFE_MODE · RECOVERY`. Chaque service a son état :
`RUNNING` (agent) · `SUSPENDED` · `BLOCKED` (bus externe) · `ONLINE` (données/CRM/audit).

## 2. Le flux d'acceptation (prouvé, test + API live)

```
AI_FIRST → incident critique → SAFE_MODE
  → agents suspendus · actions externes bloquées
  → CRM / données métier / audit TOUJOURS en ligne
  → l'humain opère (who/what/when/why enregistrés)
  → [rendre la main] → RECOVERY : HELYOS relit l'état → MemoryEvent (le Planner replanifie)
  → AI_FIRST (retour explicite et audité)
```

Vérifié en direct via l'API : `AI_FIRST → POST /os/manual → MANUAL_OVERRIDE → POST /os/resume →
AI_FIRST` (dernier handover audité = `return_ai`).

## 3. Six invariants verrouillés (tests)

1. **SAFE_MODE ne coupe jamais** la base / CRM / données métier / audit (`DATA_SERVICES` forcés `ONLINE`).
2. **Pas de système parallèle** : les LECTURES ne sont jamais bloquées → humain et IA voient les mêmes données.
3. Toute reprise humaine enregistre **who / what / when / why** (`Handover`).
4. **Pas de reprise silencieuse** : `MANUAL/SAFE → AI_FIRST` passe obligatoirement par `RECOVERY`
   (relecture) qui émet un **MemoryEvent** avant de rendre la main.
5. Un agent **`SUSPENDED` ne peut plus** envoyer / payer / publier / exécuter : la garde de
   gouvernance renvoie `DENY / OPS-SUSPENDED`.
6. Le retour est **explicite et audité** (`return_ai` avec actor + raison).

## 4. Garde d'exploitation dans la gouvernance

`GovernanceService` reçoit le contrôleur ; **avant** la politique A0–A5, `operations.gate(action)`
bloque un agent suspendu (`OPS-SUSPENDED`) ou toute action externe en SAFE MODE global
(`OPS-SAFE`). Les `READ`/`ANALYZE` passent toujours (invariants 1 & 2). Câblé pour tous les
agents via `context.py`.

## 5. Granularité (un incident Sales n'arrête pas Finance)

`enter_safe_mode(scope=["sales_agent"])` : `sales_agent` SUSPENDED, `finance_agent` RUNNING,
CRM ONLINE. Finance peut continuer à opérer (soumis à la gouvernance normale). Le SAFE MODE
**global** (scope absent) suspend tout et bloque le bus externe.

## 6. Branché au BrickRegistry (zéro coquille vide)

`manual_override` et `safe_mode` ne sont `ACTIVE` que si `readiness()` est vrai (machine à états
+ audit + suspension + handover + restore ; incident + externes bloqués + services métier en
ligne + recovery). Ils passent donc de `MISSING` à **`ACTIVE`** — prouvé par le code et les tests,
pas par une carte d'UI. Le cockpit lit `/os/operations` ; le bouton bascule un état réel.

## 7. Portée honnête & suite

- **Pré-IAM** : aujourd'hui l'endpoint n'authentifie pas *qui* reprend la main — c'est
  exactement ce que l'**IAM natif minimal** (jalon suivant) va sécuriser (qui, sur quel
  business/département, jusqu'à quel niveau).
- `reread()` est un hook : la **replanification** complète du Planner sur MemoryEvent viendra
  avec le CRM réel qui aura de vraies opérations à reprendre.
- **Front A (CFG interprocédural)** devra prouver qu'un agent `SUSPENDED` ou un bus `BLOCKED`
  n'a **aucun chemin détourné** vers une action externe — c'est le complément sécurité.

Voir [[HELYOS-System-Registry]], [[HELYOS-Enterprise-Cockpit]], [[HELYOS-Critical-Property-AST]].
