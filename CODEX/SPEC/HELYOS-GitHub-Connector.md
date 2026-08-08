# HELYOS — Connecteur GitHub réel + analyse logicielle (brique #4)

- **Statut** : Accepted · **Date** : 2026-08-02
- **Implémentation** : `world/toolbus.py` (GitHubConnector + analyses) · **Tests** : `test_toolbus.py`

---

## 1. Une vraie source distante

`GitHubConnector` lit le dépôt **distant** via l'API publique GitHub (repos publics : sans
authentification). Ops : `repo`, `commits`, `issues`, `pulls`, `languages`. Lecture réseau réelle,
gouvernée par le Tool Bus (ANALYZE/A1). Échec réseau = résultat honnête, jamais de crash.

Vérifié en direct : `Ninht-cmd/HELYOS` · Python · public · dernier commit distant = le précédent push.

## 2. Analyse logicielle réelle (au-delà des TODO/FIXME)

`ProjectConnector` gagne des **analyses statiques** (des SIGNAUX, pas des certitudes) :
- **`untested`** : modules dont le nom n'apparaît dans aucun test → tests manquants probables
  (trouvés en vrai : `dashboard, persona, schemas, telemetry, postgres_store, llm_bench`…).
- **`large`** : modules volumineux (routes.py 703 l, jarvis.py 702 l…) — signal de complexité.
- **`deadcode`** : défs de haut niveau jamais référencées ailleurs — **heuristique** (faux positifs
  connus : ex. les handlers de route FastAPI, appelés par décorateur ; d'où « probable »/« candidat »).

## 3. Le scénario d'acceptation (sur le dépôt réel)

```
« Analyse HELYOS et trouve une amélioration utile »
1. dev/read     → GitHub API : Ninht-cmd/HELYOS · Python · 2★ · poussé 2026-08-08 · 3 commits   (conf 0.90)
2. dev/analyze  → 10 améliorations réelles ; priorité : tests manquants pour « dashboard »       (conf 0.82)
3. dev/propose  → « ajouter des tests pour dashboard » — REQUIRE_VALIDATION (GR-2), en attente    (conf 0.60)
→ décision enregistrée (proposed) ; après validation+exécution : OutcomeRecord + scorecard mesurent
  si le dev_agent avait raison.
```

Chaîne complète : `GitHub → Tool Bus → Dev Agent → Planner/Orchestrateur → Memory → Governance →
Outcome → Scorecard ↺` — le cycle observe → se souvient → raisonne → propose → agit sous validation →
mesure → apprend, sur son propre code.

## 4. Portée honnête

- **Lecture** GitHub réelle ; l'**écriture** (commit/PR) reste une action gouvernée non automatisée.
- Le connecteur MCP GitHub officiel (OAuth) n'est pas utilisable en session non interactive ; on passe
  par l'**API publique** (repos publics, 60 req/h non authentifié) — suffisant pour lire ce dépôt.
- `deadcode` est une **heuristique** avec faux positifs (entrées dynamiques, décorateurs) — à raffiner
  (AST, graphe d'appels) ; `untested` et `large` sont fiables.
- « Analyser issues/PR » lit les métadonnées ; pas encore d'analyse profonde du diff.

## 5. Suite (ordre adopté)

GitHub réel **(fait)** → **dev_agent profond** (AST, contrats inter-modules, dette, CI) → **confiance
composite** (données × modèle × fiabilité agent × fraîcheur — maintenant qu'il y a des données réelles à
calibrer) → Gmail/Calendar → plus d'agents → multimodal → interface Jarvis.

Voir [[HELYOS-ToolBus-Connectors]], [[HELYOS-Outcome-Loop]], [[HELYOS-Unified-Memory-v1.0]].
