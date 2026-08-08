# HELYOS — Tool Bus & connecteurs réels (brique #4, début)

- **Statut** : Accepted · **Date** : 2026-08-02
- **Implémentation** : `world/toolbus.py` · **Tests** : `test_toolbus.py` (7) + `test_planner.py` (dev)

---

## 1. L'architecture commune

Les agents ne parlent pas directement aux outils : ils passent par un **Tool Bus gouverné**.
- Toute **lecture** = action `ANALYZE` (A1) — refusée en deçà, tracée.
- Toute **action externe/écriture** → `propose_action` → `REQUIRE_VALIDATION` (GR-2), jamais autonome.
- Un connecteur = un objet avec `read(op, **params)`. Gmail/Calendar/GitHub-API/SQL suivront ce patron.

## 2. Premier connecteur réel — `ProjectConnector`

Lit l'état **réel** du dépôt HELYOS (git local + système de fichiers), sans authentification ni réseau :
`commits`, `status` (fichiers modifiés), `search` (TODO/FIXME), `modules`, `tests`. Une source réelle,
fiable, pour démarrer la brique #4.

## 3. Preuve — le scénario que tu décris, sur le vrai dépôt

Objectif : *« Analyse HELYOS, trouve un problème, prépare un correctif, demande l'autorisation. »*
```
1. [dev/read]     Dépôt lu : 3 commits récents, 5 fichiers modifiés, 91 modules.   conf 0.88 · git local
2. [dev/analyze]  5 marqueurs TODO/FIXME — problèmes candidats.                     conf 0.80 · git local
3. [dev/propose]  Correctif préparé (diff + test) — REQUIRE_VALIDATION (GR-2).       conf 0.60
→ en attente de ta validation avant toute écriture/commit.
```
L'agent **observe réellement**, planifie, et **attend l'autorisation** avant l'action sensible.

## 4. Correctif au passage (défaut signalé)

`supply_chain_agent` a désormais de **vrais comportements différents** par sous-objectif :
`analyze` → diagnostic de dérive ; `compare` → classement des fournisseurs ; `simulate` → impact
chiffré (point de commande / coût). Les 3 étapes ne renvoient plus la même analyse.

## 5. Portée honnête

- **Un** connecteur réel (dépôt local). Gmail/Calendar/**GitHub-API**/SQL/REST suivent le même patron,
  mais exigent une **authentification (OAuth)** qui ne peut pas se faire dans une session non
  interactive — à autoriser côté connecteurs claude.ai ou via `claude mcp`.
- La lecture du dépôt est réelle ; l'**exécution** d'un correctif (écriture/commit) reste une action
  gouvernée en attente de validation — non encore automatisée.
- « Trouver un problème » = marqueurs TODO/FIXME + état git, pas encore une analyse statique profonde.

## 6. Ordre recommandé (adopté)

connecteurs réels (ici) → mémoire long terme unifiée → agents réellement spécialisés (supply corrigé) →
multimodal → interface Jarvis. Chaque connecteur futur = un `read(op)` de plus sur le bus, routé par
l'orchestrateur.

Voir [[HELYOS-Planner-Orchestrator]], [[HELYOS-Supply-Chain-Agent]], [[ADR-0012]] (client MCP).
