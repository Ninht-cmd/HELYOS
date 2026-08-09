# HELYOS — Runtime-truth : l'AST propose, le runtime arbitre

- **Statut** : Accepted · **Date** : 2026-08-08
- **Implémentation** : `world/coverage_fusion.py` (CoverageTruthResolver, verify_coverage) +
  `world/behavioral_coverage.py` + ranking dans `planner.py` · **Tests** : `test_runtime_truth.py` (5)

---

## 1. La règle

Après le signal `TestCoverageMapper = 0.034`, on acte : **AST = générateur d'hypothèses, runtime =
arbitre**. Une hypothèse statique « probablement non testé » n'a plus le statut de vérité ; l'exécution
tranche.

## 2. `CoverageTruthResolver` — sémantique fine

`0 % → confirmed` · `haute couverture → contradicted` · `intermédiaire → partial` · `non mesuré → unknown`.
**Sans mettre le runtime à 1.0 aveuglément** : `coverage.py` prouve qu'une ligne s'exécute, pas qu'un
comportement est vérifié. On distingue donc **exécuté ≠ testé avec assertion** — un `contradicted` sur un
symbole jamais nommé par un test porte la nuance « exécuté transitivement, validation comportementale non
prouvée ». On sépare `executed / covered / asserted / behavior_validated`.

## 3. La boucle complète (`verify_coverage`)

AST génère les « untested » → `coverage.py` tranche → les verdicts deviennent des **OutcomeRecord** →
la fiabilité de l'analyseur se **calibre sur des faits d'exécution**. Le finding fautif est **conservé**
(trace des erreurs de raisonnement), pas supprimé.

## 4. Ranking — un mauvais analyseur coule

Le `dev_agent` classe désormais les candidats par **fiabilité mesurée de l'analyseur**. Un analyseur à
0.036 peut encore proposer un candidat, mais ne fait **jamais** remonter seul une priorité critique :
`runtime-confirmé > AST non vérifié > analyseur historiquement mauvais`.

## 5. Couverture COMPORTEMENTALE (composants sensibles)

Pour la gouvernance/mémoire/planner, « 90 % de lignes » ne suffit pas. Des sondes exécutent le vrai code
et vérifient les **garanties** :
`EXTERNAL_SENSITIVE→REQUIRE_VALIDATION (GR-2)` · `DELETE sans backup→DENY (GR-1)` ·
`FINANCIAL→REQUIRE_VALIDATION (GR-7)` · `SELF_PERMISSION→DENY (GR-3)` · `mémoire rejected→pas de re-proposition`.
Couverture quantitative **+** comportementale = vérité solide.

## 6. Preuve (dépôt réel)

```
verify_coverage : 52 contradicted · 11 partial · 0 confirmed → fiabilité TestCoverageMapper 0.036
Ranking : priorité #1 = [complexity/high] — « untested » ne remonte plus (démotée par la fiabilité)
Scénario B (0% critique) : CONFIRMED · conf 0.99 · « code CRITIQUE jamais exécuté (couche sensible) »
Couverture comportementale : 5/5 garanties (GR-2/GR-1/GR-7/GR-3 + mémoire→plan)
```

## 7. Portée honnête

- Le runtime dit « exécuté », pas « bien testé » ; la vraie sémantique d'assertion (`behavior_validated`)
  exige d'analyser les `assert` des tests — amorcé (distinction exécuté/assermenté), pas encore complet.
- Le mapping statique reste un **générateur de candidats** (poids de preuve abaissé à 0.60), pas une vérité.
- La couverture de branches est collectée mais pas encore croisée finement avec les branches critiques.

## 8. Suite — CI (juste derrière)

Hiérarchie de vérité désormais : `heuristique → AST → runtime local → CI distante → outcome`.
Prochaine étape : **CI failure diagnosis** — lire les runs GitHub Actions, rattacher une panne à un
workflow/job/test/exception/fichier/symbole/commit, et à une éventuelle décision HELYOS antérieure →
diagnostic + confiance + proposition sous GR-2.

Voir [[HELYOS-Coverage-Fusion]], [[HELYOS-Composite-Confidence]], [[HELYOS-AST-Analysis]].
