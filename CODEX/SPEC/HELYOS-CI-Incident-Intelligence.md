# HELYOS — CI incident intelligence (du FAIL au diagnostic)

- **Statut** : Accepted · **Date** : 2026-08-08
- **Implémentation** : `world/ci_diagnosis.py` + `GitHubConnector` (runs/jobs) + `.github/workflows/tests.yml`
- **Tests** : `test_ci.py` (5) · **Hiérarchie de vérité** : heuristique → AST → runtime local → **CI distante** → outcome

---

## 1. Reconstruire la chaîne causale, pas juste « rouge »

```
run → job → test → traceback → exception → fichier/symbole → commit fautif probable
→ finding antérieur ? → décision HELYOS liée ? → diagnostic + confiance → GR-2
```

## 2. Multi-signaux (ne pas accuser le dernier fichier trop vite)

`diagnose()` accumule : (1) l'échec lui-même, (2) le **frame source** du traceback (pas le fichier de
test), (3) le **commit récent** qui a touché ce fichier (git), (4) une **décision HELYOS** antérieure
liée au symbole/fichier (mémoire). La **confiance de diagnostic monte avec l'accord des signaux**.
Trois niveaux : observation (le test a échoué ?) · diagnostic (est-ce cette régression ?) · action
(le correctif aidera-t-il ?).

## 3. Auto-contradiction (le système se remet en cause)

Si la CI casse juste après une décision jugée « faible risque », `record_ci_outcome()` fait redescendre
cet outcome dans la mémoire → le **scorecard du dev_agent baisse**. Symétriquement, une CI verte après
correction **confirme** la décision.

## 4. Preuve — bout en bout sur artefacts RÉELS

Régression volontaire d'une règle GR-2, puis CI locale exécutée (sous-processus, comme la CI) :
```
CIRun : failure · 6 ok / 1 échec
CI FAILURE :
  Test      test_confidence_never_bypasses_governance
  Exception AttributeError: 'Action' object has no attribute 'simplified_gr2'
  Fichier   governance/policy.py:97 dans evaluate      (frame SOURCE extrait du traceback réel)
  Commit    27ebca2                                    (git : dernier commit du fichier)
  Décision  DEC-0002 « simplifier la règle GR-2 »       (mémoire : décision liée)
  Diagnostic « Régression probable dans evaluate, introduite par 27ebca2, liée à DEC-0002. »
  Confiance observation 0.99 · diagnostic 0.91 · action 0.728
  → écriture du correctif = REQUIRE_VALIDATION (GR-2), en attente
Après restauration : CI verte (7/0) → outcome CONFIRMÉ ; policy.py restauré à l'identique.
CI distante : lecture réelle des runs GitHub Actions (42 runs).
```

### 4.1 Recalibration du dev_agent — test d'acceptation PERMANENT (déterministe)

`test_ci_acceptance.py` fige le scénario complet et le rend reproductible (arbre « canary »
temporaire, aucun fichier réel touché, pas de réseau/horloge) : panne CI → diagnostic →
correctif sous GR-2 → retour au vert → **l'Outcome recalibre le dev_agent, chiffres à l'appui**.

`calibration = bayésien(confirmés, rejetés) = (c+2)/(c+r+4)` — la mesure bouge dans les deux sens :
```
calibration dev_agent AVANT           : 0.50
CIRun (rouge)   failure · 1 échec parsé
diagnostic      AttributeError dans gr2_required (frame SOURCE, pas le test) -> décision liée DEC-0002
confiances      observation 0.99 · diagnostic 0.79 · action 0.632
correctif       require_validation (GR-2)            ← jamais autonome
calibration APRÈS panne (décision rejetée)   : 0.40  ← la CI cassée CONTREDIT la décision
CIRun (vert)    success · 2 ok / 0 échec
calibration APRÈS vert (décision confirmée)  : 0.50  ← RECALIBRATION à la hausse
```
La boucle « changement → panne → décision → correction → résultat » est ainsi **fermée et
mesurée** : le dev_agent ne se contente pas d'échouer, il est recalibré par le retour au vert.

## 5. CI réelle branchée

`.github/workflows/tests.yml` exécute la suite à chaque push/PR → HELYOS dispose désormais d'une preuve
d'exécution **distante et indépendante** (couche « CI distante »). `GitHubConnector.read("runs"/"jobs")`
lit les runs Actions publics.

## 6. Portée honnête

- Le parsing couvre `unittest` ; un vrai pipeline lirait aussi les **logs de job** Actions (souvent
  derrière auth pour les logs bruts — les métadonnées de run/job sont publiques).
- « Commit fautif » = dernier commit du fichier (signal), pas une **bissection** (git bisect = raffinement).
- Le diagnostic relie une décision par symbole/fichier ; une vraie imputation causale (quel diff a changé
  le comportement) viendra avec le **diff coverage / changed-lines coverage en CI**.

## 7. Suite

**Diff coverage + changed-lines coverage en CI** : les lignes introduites par une **décision HELYOS**
sont-elles réellement testées avant d'être considérées sûres ? C'est la preuve la plus utile après la
couverture globale — et elle ferme la boucle « changement → panne → décision → correction → résultat ».

Voir [[HELYOS-Runtime-Truth]], [[HELYOS-Coverage-Fusion]], [[HELYOS-Composite-Confidence]].
