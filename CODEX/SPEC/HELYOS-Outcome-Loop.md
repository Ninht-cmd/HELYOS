# HELYOS — Boucle outcome → plan (résultat réel qui adapte la décision)

- **Statut** : Accepted · **Date** : 2026-08-02
- **Implémentation** : `world/outcome.py` + orchestrateur · **Tests** : `test_outcome.py` (4)
- **Critère d'acceptation** : ✅ comportemental — réutilise le gain, ne répète pas la décision, cherche d'autres leviers.

---

## 1. Ce que ça ferme

« HELYOS se souvient » → « HELYOS **compare prévu ↔ réel, comprend l'écart, adapte le plan, mesure à
nouveau** ». La boucle complète : `OBSERVE → REMEMBER → PLAN → DECIDE → ACT → MEASURE → LEARN → ADAPT ↺`.

## 2. Synthèse, pas 50 événements bruts — `OutcomeInsight`

Le Planner reçoit des insights synthétiques (objectif, attendu, observé, delta, **ratio R**, decision_id,
statut, leçon, confiance, `reusable`). Ratio `R = observé / attendu` ; catégories **configurables par
domaine** (un enjeu médical/financier n'a pas les tolérances d'un enjeu logistique) :
`R≥0.95 success · 0.50–0.95 partial_success · 0–0.50 weak_success · R≤0 failure`.

## 3. Attacher l'outcome à la décision qui l'a provoqué

`OBJECTIVE → DECISION → OUTCOME (expected/observed/status)`. On peut donc demander « quelles décisions
supply-chain ont **réellement** marché ? », pas seulement « quels documents ressemblent à ma question ».

## 4. Preuve — le test comportemental (pas juste « l'outcome est présent »)

```
RUN #1  « Réduire les coûts de 15% » → décision « Passage vers FRN-12 » (proposed)
        → validée → OUTCOME mesuré : attendu −15% · observé −11.8% · confirmed (partiel)

RUN #2  « Continue à réduire mes coûts »
  Mémoire pertinente : « Décision : Passage vers FRN-12. Attendu 15 ; Observé 11.8 ;
     Écart restant : 3.2 points ; Ratio : 78.7% ; État : partial_success. »
  Comportement : reuse_gain=True · répète FRN-12=False · nouveaux leviers=4
  Nouveau plan : 1. conserver le gain · 2. transport · 3. taille commandes · 4. stock sécurité
                 · 5. simuler la combinaison · 6. proposer (hors décision déjà prise)
```

Asserts vérifiés : `"3.2" in memory_context` · `reuses_confirmed_gain` · `not repeats("Passage vers FRN-12")`
· `nouveaux_leviers ≥ 2`.

## 5. Deuxième boucle — performance des agents (métacognition)

`agent_scorecard` : par agent, nb de décisions, résultats confirmés, ratio moyen, **confiance calibrée**.
Ex. `supply_chain_agent : 1/1 confirmé · confiance calibrée 1.0`. La confiance cesse d'être seulement
locale ; elle intègre l'historique réel de l'agent — début de vraie métacognition (« sur N décisions
similaires, M ont produit le résultat attendu »).

## 6. Portée honnête

- Rappel par similarité vectorielle (cosinus local) + entités ; pas encore de raisonnement temporel fin.
- La confiance calibrée est le **taux de confirmation** ; pas encore une combinaison (données × modèle ×
  fiabilité agent × fraîcheur) — c'est le prochain raffinement.
- Les « nouveaux leviers » (transport, EOQ, stock) sont des étapes d'analyse **génériques** pour l'instant,
  pas encore chiffrées par un domaine dédié.

## 7. Suite (ordre adopté)

Boucle outcome **(fermée)** → GitHub-API réel (OAuth requis, hors session) → Gmail/Calendar → agents
spécialisés → multimodal → interface Jarvis. Désormais chaque connecteur ajouté **alimente une boucle
mature** (observe → mémorise → planifie → décide → agit → mesure → apprend → adapte).

Voir [[HELYOS-Unified-Memory-v1.0]], [[HELYOS-Planner-Orchestrator]], [[HELYOS-Model-Governance-v1.0]].
