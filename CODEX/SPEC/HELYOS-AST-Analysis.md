# HELYOS — Moteur d'analyse AST (findings avec preuve)

- **Statut** : Accepted · **Date** : 2026-08-02
- **Implémentation** : `world/ast_analysis.py` · **Tests** : `test_ast.py` (8) · **Branché** : Tool Bus → dev_agent

---

## 1. De « suspect » à « constat avec preuve »

Fin des heuristiques TODO/FIXME : un **index AST** alimente quatre analyseurs qui produisent des
`Finding` normalisés (id, catégorie, sévérité, **confiance**, fichier, symbole, **preuves[]**, recommandation).

## 2. Les quatre analyseurs

- **ImportGraphAnalyzer** : graphe d'imports internes → **imports cassés** (relatifs non résolus),
  **cycles**, et **invariants architecturaux**.
- **DeadCodeAnalyzer** (contextuel) : table des symboles + cas spéciaux — un symbole **décoré**
  (`@router.get`), dans `__all__`, ou point d'entrée n'est **jamais** dit mort (faux positifs FastAPI éliminés).
- **ComplexityAnalyzer** : complexité cyclomatique (`+1` par `if/for/while/except/and|or/case/ternaire`).
  Un **signal**, pas un bug.
- **TestCoverageMapper** : parse l'AST des tests → symboles source **réellement référencés** → approx.
  de couverture statique (bien meilleure que « pas de test_X.py »).

## 3. Le cœur pour HELYOS — invariants de couche

Déclarés et **vérifiés par l'AST** : `governance` ne dépend jamais de `agents/api/world` ; `memory` ne
dépend jamais de l'`api` ; le noyau reste bas niveau. Une violation ne serait pas « du mauvais code » :
elle pourrait **casser les garanties d'autonomie/gouvernance**. **Vérifié : 0 violation** — les couches tiennent.

## 4. Preuve — HELYOS analyse son propre dépôt

```
99 findings : complexity 9 · import_cycle 2 · dead_code 28 · untested 60 ; 0 architecture · 0 broken_import
Exemples (avec preuve) :
  [import_cycle] context → pulse → context
  [complexity/high conf 0.95] analyze — complexité cyclomatique = 26 (≥ 12)     ← auto-critique honnête
  [untested] Agent — symbole public sans référence dans les tests
  [dead_code] LiteLLMAdapter — défini, jamais référencé, non décoré

dev_agent : « 20 findings AST ; priorité [complexity/high] analyze — Découper (preuve : CC=26) »
            → propose (avec preuve) → REQUIRE_VALIDATION (GR-2).
```

## 5. Le cycle Finding → Decision → Outcome (déjà branché)

Le finding devient une **décision** en mémoire (symbole en entité) → gouvernance → après
validation/exécution, un `OutcomeRecord` + le **scorecard** mesurent si le `dev_agent` avait raison
(précision observée). C'est la donnée qui préparera la **confiance composite**.

## 6. Portée honnête

- `deadcode` reste conservateur : les symboles utilisés dynamiquement (registres de plugins, imports
  dynamiques) peuvent apparaître — d'où « vérifier si mort », pas « supprimer ».
- Les cycles trouvés (`context↔jarvis`, `context↔pulse`) sont **réels** au sens des imports (souvent
  gérés par imports locaux à l'exécution) — de vrais constats à traiter, pas des faux positifs.
- Couverture = **statique** (référence de symbole) ; la couverture **dynamique** (`coverage.py`) viendra ensuite.
- L'écriture d'un correctif reste **gouvernée non automatisée**.

## 7. Suite

AST **(fait)** → **confiance composite** (`evidence_quality × analyzer_reliability × agent_calibration ×
source_freshness` — maintenant qu'il y a des findings réels + des outcomes pour calibrer) → couverture
dynamique → Gmail/Calendar → plus d'agents.

Voir [[HELYOS-GitHub-Connector]], [[HELYOS-Outcome-Loop]], [[HELYOS-ToolBus-Connectors]].
