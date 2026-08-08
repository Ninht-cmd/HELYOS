# HELYOS — Fusion AST ↔ runtime (coverage.py)

- **Statut** : Accepted · **Date** : 2026-08-08
- **Implémentation** : `world/coverage_fusion.py` + `world/coverage_runner.py` · **Tests** : `test_coverage.py` (6)

---

## 1. Confronter la croyance statique à l'exécution réelle

L'AST *croit* qu'un symbole est « probablement non testé » ; `coverage.py` *montre* ce qui est
réellement exécuté. La fusion transforme une hypothèse en **verdict vérifiable** :
`0 % → confirmed` · `haute couverture → contradicted (faux positif)` · sinon `partial`.

## 2. Ce que ça produit

- **`RuntimeCoverageFinding`** : fichier, symbole, lignes totales/couvertes, %, prédiction statique,
  verdict runtime, preuves.
- **OutcomeRecord automatiques** : un verdict `confirmed` = +1 confirmé pour l'analyseur ; `contradicted`
  = faux positif enregistré → la **fiabilité de l'analyseur se calibre sur des faits d'exécution**, sans
  attendre une validation humaine.
- **Priorité pondérée par la criticité** : `Priority = Risk × (1 − Coverage) × Confidence`. Une couche
  critique partiellement couverte passe **avant** un utilitaire d'UI à 0 % (gouvernance 55 % → 0.42 >
  UI 0 % → 0.38). HELYOS ne dit pas « 0 % = priorité max ».
- **Couverture des lignes MODIFIÉES** (bien plus utile que le delta global).

## 3. Preuve — et un constat honnête sur HELYOS lui-même

`coverage.py 7.14.3` mesure la suite réelle (12 s). Confrontation des 61 findings « untested » de l'AST :

```
Verdicts runtime : 55 contradicted · 6 partial · 0 confirmed
Ex. Agent, AgentRegistry (agents/base.py) : annoncés non testés → 97 % couverts (exercés indirectement)
    OllamaLLM (agents/llm.py) : 100 %
Calibration auto : 0 confirmés / 55 faux positifs → fiabilité TestCoverageMapper = 0.034
```

**Le runtime a révélé que mon analyseur `TestCoverageMapper` est peu fiable** : il flagge « le nom du
symbole n'apparaît pas dans les tests » alors que le symbole est **exécuté transitivement** (import,
appel indirect). La confiance composite présentera donc désormais les findings « untested » avec une
**très faible fiabilité (0.034)** — HELYOS a appris à se méfier de cet analyseur. C'est précisément le
comportement recherché : **vérifier ses propres hypothèses et douter correctement.**

(Le scénario « confirmed à 0 % » est démontré dans les tests déterministes ; en dépôt réel presque rien
n'est à 0 % car tout module importé exécute ses `def/class` — d'où 0 confirmed live, honnêtement.)

## 4. Portée honnête

- Prochaine amélioration évidente, **désignée par le runtime lui-même** : remplacer le mapping
  « nom dans les tests » par une **atteignabilité via le graphe d'imports/appels** (le static mapper
  doit devenir fiable, ou être remplacé par la couverture runtime comme source de vérité).
- La couverture de branches est collectée (`branch=True`) mais pas encore exploitée finement
  (la branche `if action.sensitive: submit(...)` mérite un traitement dédié — criticité).
- `CIRun` est défini (normalisation) ; la lecture réelle des runs CI (GitHub Actions API) + le
  **diagnostic de panne** (rattacher un échec à un commit/test/finding/décision) est l'étape suivante.
- Ne pas compter `coverage.py` local + le même en CI comme deux preuves indépendantes (corrélées).

## 5. Suite

Coverage runtime **(fait)** → **fiabiliser/replacer le TestCoverageMapper** (le runtime devient la vérité)
→ **CI failure diagnosis** (lire les runs, rattacher une panne à sa cause) → couverture de branches
critiques.

Voir [[HELYOS-AST-Analysis]], [[HELYOS-Composite-Confidence]], [[HELYOS-Outcome-Loop]].
