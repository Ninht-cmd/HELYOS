# HELYOS — Mutation testing ciblé (les tests détectent-ils une ligne fausse ?)

- **Statut** : Accepted · **Date** : 2026-08-09
- **Implémentation** : `world/mutation_testing.py` · `world/confidence.py` (facteur `mutation_score`)
- **Tests** : `test_mutation.py` (10)
- **Hiérarchie de vérité** : … → couverture du diff (exécution) → **mutation (pouvoir de détection)** → outcome

---

## 1. Le trou que la couverture de diff ne bouche pas

La couverture de diff prouve qu'une ligne critique **s'exécute**. Elle ne prouve pas que les
tests la **vérifient** : un test peut exécuter la ligne GR-2 sans jamais asserter son résultat.
La mutation comble ce trou — sous **règle stricte** : on ne mute pas « pour un score », on mute
pour éprouver une **propriété critique précise**.

```
diff critique détecté → ligne/propriété ciblée → mutants contrôlés → tests CIBLÉS
   → mutant tué ?  ── oui → preuve forte
                    └─ non → SURVIVANT : produire des HYPOTHÈSES, jamais « bug confirmé »
```

## 2. Opérateurs sémantiques (dangereux et simples)

`REQUIRE_VALIDATION→ALLOW` · `"require_validation"→"allow"` · `DENY→ALLOW` ·
`sensitive=True→False` · `validated=False→True` · `has_backup=False→True` ·
`if COND:→if not (COND):`. On ne mute **jamais** un token de **commentaire** (`_split_comment`) —
ce serait une mutation équivalente, un survivant garanti qui bloquerait `CONFIRMED` à tort.

## 3. Le survivant n'est pas un bug

Sur un survivant, HELYOS **ne conclut pas à un bug**. Il liste les causes possibles et demande un
diagnostic :

```
Survivant détecté (confiance 0.4).
Hypothèses : 1. test insuffisant  2. mutation équivalente
             3. branche inatteignable  4. propriété non couverte
Action : diagnostic supplémentaire requis.
```

`record_mutation_outcome` d'un survivant critique est **neutre** pour la calibration (événement
de diagnostic, ni crédit ni pénalité). Un mutant tué porte une confiance forte (0.95).

## 4. La mutation ne remplace pas les autres preuves

`change_assurance = CI × diff × critique × comportement × fiabilité × mutation_score` (produit ;
`mutation_score=1.0` par défaut = neutre). Et `gated_change_verdict` ne peut que **dégrader** :

```
CHANGE_CONFIRMED  seulement si  aucun mutant critique ne survit sans explication.
```
Le portail ne promeut jamais et ne sauve jamais une CI rouge.

## 5. Preuve

**Acceptation (sous-processus réels, deux temps)** — un test faible qui exécute la ligne GR-2
sans asserter sa valeur :
```
A) test faible : le mutant REQUIRE_VALIDATION→ALLOW SURVIT
   → confirmed_ok = False → gated(CONFIRMED) = CHANGE_NOT_SUFFICIENTLY_VALIDATED
     (alors même que diff = 100 %, CI verte, sonde comportementale verte)
B) test ciblé ajouté : le même mutant est TUÉ
   → mutation_score = 1.0 → gated(CONFIRMED) = CHANGE_CONFIRMED
```
Ce que ça prouve : le test n'exécute plus seulement la ligne, il **détecte qu'elle est fausse**.

**Dépôt réel** — mutation de la vraie ligne GR-2 de `governance/policy.py:140`
(`Decision.REQUIRE_VALIDATION → Decision.ALLOW`), tests `test_governance.py` lancés :
```
RÉSULTAT : KILLED · mutation_score 1.0 · policy.py restauré à l'identique (sha256 + diff vides)
```
Les tests de gouvernance d'HELYOS **détectent** réellement une règle GR-2 cassée.

## 6. Sûreté

Chaque mutant est écrit puis **restauré dans un `finally`** ; les octets d'origine sont relus et
comparés (échec dur si la restauration diffère). Vérifié même quand le sous-processus de test
lève une exception. Prévu pour un arbre jetable ; sur le vrai dépôt, la fenêtre de mutation est
courte et l'appelant l'assume.

## 7. Portée honnête & suite

- Opérateurs volontairement **restreints** aux propriétés de gouvernance (pas un moteur de
  mutation généraliste) — c'est la règle « muter pour une propriété », pas pour un score.
- L'équivalence n'est pas prouvée automatiquement (indécidable) : un survivant est **signalé
  pour diagnostic**, pas classé.
- La cible « ligne critique » dépend encore des marqueurs de `diff_coverage`. **Prochain brick** :
  détection **AST** des propriétés critiques, pour capturer une logique GR-2 où qu'elle vive
  (`world/toolbus.py` compris), et ne plus dépendre du chemin `governance/`.

Voir [[HELYOS-Diff-Coverage]], [[HELYOS-CI-Incident-Intelligence]], [[HELYOS-Composite-Confidence]].
