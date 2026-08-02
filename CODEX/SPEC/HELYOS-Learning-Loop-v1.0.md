# HELYOS Learning Loop v1.0 — fermer la boucle simulation ↔ réalité

- **Statut** : Accepted (moteur implémenté + testé) · **Date** : 2026-08-02
- **Implémentation** : `world/learning.py` · **Tests** : `test_learning.py` (6) · **Étend** : Simulation v1.3, DD-0001 (Phase C)

---

## 1. Le verrou levé

Jusqu'ici, les lois causales (ex. `coût ≈ 1.6·prix`) étaient **écrites par le développeur**. C'est le
plafond : un système qui ne fait que simuler un modèle figé ne s'améliore jamais. Cette couche ferme la
boucle — HELYOS **apprend ses lois des résultats réels** :

```
Observation → Knowledge Graph → Simulation → Décision → Exécution → Résultat réel
   → mesure de l'erreur → mise à jour des coefficients → NOUVEAU modèle du monde
```

## 2. Le mécanisme (régression bayésienne récursive)

Une `CausalLaw` `y ≈ a·x` porte son coefficient `a` comme **croyance gaussienne** `N(mean, σ²)`.

- **`predict(x)`** → `ŷ = a·x` et son incertitude `σ = √((x·σ_a)² + σ_bruit²)` (incertitude du
  coefficient **+** bruit d'observation).
- **`observe(x, y)`** → mise à jour **conjuguée exacte**, une observation à la fois :
  `p_post = p_prior + x²/σ_bruit²` ; `mean_post = (p_prior·mean + x·y/σ_bruit²)/p_post` ;
  `σ_post = √(1/p_post)`. Chaque donnée resserre l'incertitude.
- **`calibration(pairs)`** → MAE, RMSE, biais, et **couverture** (fraction des réels dans ±1σ).
- **`close_loop(stream)`** → pour chaque `(x, y_réel)` : prédire → **mesurer l'erreur** → apprendre.
  Renvoie la trajectoire (coef, σ, erreur).
- **`wire_learned(graph, law)` / `relearn(graph, law, pairs)`** → la loi est branchée comme dérivation ;
  ré-apprendre **re-dérive le graphe** → le modèle du monde se corrige tout seul.

## 3. Preuve (testée + démontrée)

```
Coefficient : départ 1.000 (faux) → 1.598 après 200 observations (vérité cachée 1.6)
Incertitude : ±0.114 → ±0.006  (elle se resserre)
Calibration (données fraîches) : MAE 0.25 (≈ bruit) · biais 0.001 · COUVERTURE ±1σ = 68%
   → l'incertitude apprise est BIEN CALIBRÉE (68% est la valeur théorique gaussienne)
Graphe : cout_unitaire 5.00 (modèle naïf ×1.0) → 7.96 (appris ×1.6) — colle au réel observé
```

## 4. Portée honnête

- On apprend la **VALEUR** d'une loi dont la **FORME** (quelles variables, quel lien) est donnée. La
  **découverte de structure** (quelles arêtes causales existent, non-linéarités, retards) reste distincte.
- Modèle **pente à l'origine** `y = a·x` à bruit connu ; l'affine `y = a·x + b`, le multivarié, et
  l'estimation du bruit sont des extensions.
- Il faut un **flux d'observations réelles** (via les connecteurs + la journalisation des exécutions) pour
  que la boucle tourne en production — le mécanisme est prêt, l'alimentation est le prochain branchement.

## 5. Ce que ça change stratégiquement

C'est exactement le point que soulève le fondateur : passé le framework, la valeur d'HELYOS dépend de la
**qualité, la calibration et les données** des domaines. Cette boucle est le mécanisme qui transforme un
domaine **écrit** en domaine **calibré** : chaque exécution réelle devient une donnée qui affine les lois.
Un domaine (finance, engineering, supply…) n'est plus figé — il **converge vers la réalité** de *ce*
business précis.

## 6. Prochain palier

1. **Alimenter la boucle** : journaliser chaque (décision → résultat réel) via les connecteurs et appeler
   `relearn` → auto-calibration continue en production.
2. **Étendre le modèle** : lois affines/multivariées, estimation du bruit, puis **découverte de structure**.
3. **v1.4 Opportunity Engine** : générer/simuler/scorer des opportunités avec des lois désormais *calibrables*.

Voir [[HELYOS-Simulation-Engine-v1.3]], [[HELYOS-Domain-Layer-v2.0]], [[DD-0001]] (Phase C).
