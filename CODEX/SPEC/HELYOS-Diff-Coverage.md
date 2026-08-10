# HELYOS — Diff coverage (« vert » ≠ « prouvé »)

- **Statut** : Accepted · **Date** : 2026-08-09
- **Implémentation** : `world/diff_coverage.py` · `world/confidence.py` (`change_assurance`)
  · `world/coverage_runner.py` (`measure_coverage_paths`, lignes exécutables)
  · `world/memory_store.py` (`OutcomeRecord.assurance`)
- **Tests** : `test_diff_coverage.py` (5) + `test_confidence.py::TestChangeAssurance`
- **Hiérarchie de vérité** : heuristique → AST → runtime local → **couverture du diff** → CI → outcome

---

## 1. Le problème : une couverture globale ment sur une modification

```
Global coverage : 91 %      ← rassurant
Diff coverage du commit : 42 %   ← ce qui compte pour une décision HELYOS
```

Un agent qui ajoute une branche de gouvernance sans la tester peut garder la CI verte : il
n'a pas cassé la suite existante. « Vert » ne prouve pas que les **nouvelles** lignes sont
exercées. On rattache donc le diff à la décision qui l'a causé :

```
Décision → Patch → Commit → Lignes modifiées → Couverture runtime → CI → Outcome
```

## 2. Cinq niveaux (une agrégation ne doit jamais cacher un trou critique)

`global_coverage · module_coverage · diff_coverage · critical_diff_coverage
· behavioral_diff_validation`.

`DiffCoverageAnalyzer` parse le patch git (`parse_diff_added_lines`, robuste au format
unifié), intersecte les lignes ajoutées avec les **statements** de coverage.py, et distingue
les lignes **critiques** (couche de gouvernance + marqueur `GR-\d / REQUIRE_VALIDATION /
DENY / has_backup / sensitive …`). `DiffCoverage = lignes modifiées couvertes / lignes
modifiées exécutables`.

## 3. `change_assurance` — 4e niveau de confiance

```
change_assurance = CI × diff_coverage × critical_path_coverage × sondes_comportementales
                      × fiabilité_analyseur          (produit borné [0,1])
```
Un maillon faible écrase (une CI verte au chemin critique nu reste faible). **Garde-fou** :
cette mesure classe la qualité d'une modification ; elle ne contourne **jamais** GR-2.

Verdict rattaché à la décision :
- `CHANGE_BROKEN` — la CI casse (régression) → décision **rejetée**.
- `CHANGE_NOT_SUFFICIENTLY_VALIDATED` — vert mais diff/critique insuffisant → **NEUTRE**
  (aucun crédit de calibration malgré le vert ; journalisé).
- `CHANGE_CONFIRMED` — vert + diff ≥ 90 % + chemin critique 100 % + sonde OK → **confirmée**
  (crédit de calibration).

## 4. Preuve — scénario en deux temps (git réel + coverage.py réel)

```
calibration dev_agent AVANT            0.50

COMMIT A  branche GR-2 ajoutée, AUCUN test
  global 83% · module 83% · diff 50% · diff_critique 50%
  change_assurance 0.15  →  CHANGE_NOT_SUFFICIENTLY_VALIDATED
  calibration APRÈS A (diff-aware)       0.50   ← AUCUN crédit malgré le vert
  calibration APRÈS A (naïf « vert=OK »)  0.60   ← crédit indu que l'on évite

COMMIT B  test de la branche ajouté
  global 100% · module 100% · diff 100% · diff_critique 100%
  change_assurance 0.60  →  CHANGE_CONFIRMED
  calibration APRÈS B (diff-aware)       0.60   ← crédité (changement prouvé)
```

Le point crucial est le **contraste** : une logique « CI verte = succès » aurait crédité le
dev_agent dès le commit A (0.50 → 0.60). La couverture de diff le refuse : le module est à
83 %, mais la **ligne GR-2 elle-même n'est jamais exercée** (diff critique 50 %). Le dev_agent
n'est crédité qu'au commit B, quand le changement est réellement prouvé. Il apprend ainsi que
**« vert » ne veut pas dire « suffisamment prouvé »** — exactement ce qui empêche un agent
autonome de se congratuler pour n'avoir rien cassé.

## 5. Portée honnête

- La ligne « critique » est détectée par **couche + marqueur textuel** (heuristique
  documentée), pas par analyse sémantique de flot ; un raffinement possible est de repérer les
  branches critiques via l'AST plutôt que par motif.
- `diff_coverage` mesure l'**exécution** des lignes modifiées, pas la présence d'une
  **assertion** dessus — d'où le niveau comportemental en complément, et la suite ci-dessous.
- La couverture de branche fine (chaque arête d'un `if`) reste au niveau du fichier ; la
  granularité par arête sur les seules lignes du diff est un raffinement.

### Durcissement (auto-revue adversariale)

La revue déléguée à des sous-agents n'a pas pu s'exécuter (limite de session) ; elle a donc été
menée en direct, par exécution de sondes. Deux **vrais bugs** trouvés et corrigés (tests de
non-régression ajoutés) :
- **parsing** : une ligne ajoutée dont le contenu commence par `++` (diff-line `+++x`) était
  confondue avec un en-tête `+++ ` → ligne perdue et numéros suivants décalés. Corrigé par une
  machine à états `in_hunk` (la structure du diff tranche, pas une heuristique de chaîne).
- **dénominateur vide** : un fichier source modifié mais **absent** du rapport coverage.py
  (nouveau module sans aucun test) laissait `diff_coverage` valoir 1.0 → **CHANGE_CONFIRMED**
  à tort. Désormais un fichier non mesuré est traité comme **non couvert** (direction sûre) :
  un module entièrement non testé ne peut jamais être confirmé.

## 6. Suite

**Mutation testing ciblé sur les lignes critiques** : vérifier non seulement que les lignes
critiques sont *exécutées*, mais que les tests **détecteraient** une mauvaise modification
(muter la ligne GR-2 → un test doit virer au rouge). C'est le complément naturel : la couverture
de diff prouve l'exécution ; la mutation prouve le **pouvoir de détection**.

Voir [[HELYOS-CI-Incident-Intelligence]], [[HELYOS-Runtime-Truth]], [[HELYOS-Composite-Confidence]].
