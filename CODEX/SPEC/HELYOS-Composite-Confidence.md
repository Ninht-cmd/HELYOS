# HELYOS — Confiance composite métacognitive

- **Statut** : Accepted · **Date** : 2026-08-02
- **Implémentation** : `world/confidence.py` + dev_agent · **Tests** : `test_confidence.py` (7)

---

## 1. La formule

`C = E × R × A × F` — E qualité de preuve · R fiabilité de l'analyseur · A calibration de
l'agent · F fraîcheur de la source. Deux lectures :
- **stricte** (produit) : un maillon faible écrase — pour les **actions sensibles** ;
- **équilibrée** (moyenne géométrique `(E·R·A·F)^¼`) : qualité globale du diagnostic.

## 2. Les quatre facteurs, sur base réelle (plus des constantes)

- **E** — poids par **nature** de preuve (invariant/AST 1.0 > cycle 0.95 > complexité 0.92 >
  mapping tests 0.82 > heuristique dead-code 0.68 > motif texte 0.45) ; petit bonus par preuve
  indépendante, borné à 1.
- **R** — **prior bayésien** `(confirmés+α)/(confirmés+rejetés+α+β)`, α=β=2. `1/1` vaut **0.60**,
  pas 1.0 ; le prior s'efface avec l'expérience. Dérivé des **outcomes** par catégorie d'analyseur.
- **A** — même prior à l'échelle du `dev_agent` (tous analyseurs). (ECE = plus tard.)
- **F** — **demi-vie par type de source** : métadonnées 7 j · code 30 j · CI 6 h · issue 2 j ·
  marché minutes. `F = 2^(−t/H)`. Une donnée d'une demi-vie vaut 0.5. Pas de constante globale.

## 3. Trois niveaux distincts (crucial)

- **observation** (« le fait est-il vrai ? ») = E → `analyze a CC=26` : quasi certain.
- **diagnostic** (« est-ce un vrai problème ? ») = √(E·R).
- **action** (« la correction améliorera-t-elle ? ») = équilibrée → beaucoup plus discutable.

On sépare `confidence_finding` de `confidence_recommendation` : un fait peut être sûr (0.99) alors
que « découper en 4 fonctions » reste discutable (0.72).

## 4. Preuve — l'agent apprend à douter correctement

```
RUN #1  (priors seuls)   : globale 0.76 · stricte 0.33 | analyseur 0.60 · agent 0.60
RUN #20 (15/18 confirmés): globale 0.86 · stricte 0.56 | analyseur 0.77 · agent 0.78 | hist 15/18
Inverse (dead_code, 5 faux positifs/8) : analyseur 0.42 → findings dead_code plus PRUDENTS.
```

La confiance **monte** quand les constats se confirment, **baisse** quand un analyseur accumule des
faux positifs — la métacognition devient crédible.

## 5. Garde-fou (non négociable)

La confiance **classe, explique, priorise** — elle ne **contourne JAMAIS** la gouvernance. Une
confiance de 0.999 ne saute pas GR-2 : les règles d'or restent au-dessus (testé).

## 6. Portée honnête

- La calibration est le **taux de confirmation bayésien**, pas encore un vrai **ECE** (« quand l'agent
  dit 0.8, a-t-il raison ~80 % du temps ? ») — prochain raffinement.
- Les trois niveaux sont des **mappings** (observation=E, diagnostic=√(E·R), action=équilibrée), pas
  encore appris.
- La fraîcheur des findings de code utilise `source_code` (30 j) ; l'arbre analysé étant courant, F≈1.

## 7. Suite

Confiance composite **(faite)** → **`coverage.py` dynamique + CI** : le prochain jeu de données idéal
pour éprouver cette confiance — **preuve AST vs preuve runtime vs résultat CI réel** (E gagne une source
indépendante, R/A se calibrent sur des faits d'exécution).

Voir [[HELYOS-AST-Analysis]], [[HELYOS-Outcome-Loop]], [[HELYOS-Model-Governance-v1.0]].
