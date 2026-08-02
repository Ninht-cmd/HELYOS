# HELYOS Model Governance v1.0 — MLOps pour le World Model

- **Statut** : Accepted (moteur implémenté + testé) · **Date** : 2026-08-02
- **Implémentation** : `world/registry.py` · **Tests** : `test_registry.py` (6) · **Étend** : Learning Loop v1.0

---

## 1. Le risque adressé

Une boucle d'apprentissage sans gouvernance est dangereuse pour un système qui pilote des
décisions : on ne sait plus **pourquoi** un coefficient a bougé, on ne peut pas **revenir en
arrière** si une série de données est corrompue, ni **vérifier qu'un apprentissage améliore**
avant de l'activer. Passé l'algorithme, la traçabilité des connaissances devient aussi importante
que l'apprentissage lui-même. Cette couche est le **model registry** du World Model — dans le même
esprit que l'AuditLog de la gouvernance A0–A5 : **append-only**, tracé, réversible.

## 2. Ce qu'elle fournit

- **Versioning append-only** : `register(law)` crée une `LawVersion` immuable (coef, σ, n_obs, date,
  provenance, métriques). L'historique n'est **jamais** écrasé ; `active` désigne la version en service.
- **Promotion sous garde (champion/challenger)** : `propose(challenger, val_pairs)` évalue le challenger
  **et** le champion sur un jeu de validation **tenu à part**, et n'**active** le challenger que s'il
  **améliore** la métrique (RMSE par défaut). Sinon : enregistré mais non activé, champion conservé.
- **Comparaison** : `compare(name, va, vb, val)` — performances de deux versions côte à côte.
- **Rollback** : `rollback(name, version)` — retour à une version antérieure (historique intact, tracé).
- **Détection de dérive** : `drift(name, recent)` — flag si l'erreur récente dépasse nettement la RMSE
  enregistrée (signal de ré-apprentissage / investigation).
- **Provenance** : `explain(name)` — répond à « pourquoi ce coefficient est passé de X à Y, quelles
  observations, depuis quand actif, quelles métriques ».
- **Journal d'audit** : chaque register/promote/reject/rollback est horodaté et justifié (option : émis
  sur l'EventBus).

## 3. Preuve (cycle de vie complet, testé)

```
v1  register  coef 1.402  RMSE 0.746   (40 obs)
Challenger (300 obs) proposé, validé sur jeu tenu à part :
    PROMOTED   RMSE 0.746 → 0.199   → v2 active (coef 1.598)
Challenger issu de DONNÉES CORROMPUES (coef 2.6) :
    REJECTED   RMSE 3.69 ≥ 0.199   → champion v2 conservé
Dérive (monde réel devenu coef 2.4) :
    drift = True   RMSE récente 3.05 vs base 0.199  (×15.4)
Provenance : « cout~prix = 1.5981, v2, active, 300 obs. Passé de 1.4020 (v1) à 1.5981.
              champion_rmse 0.746 → challenger 0.199 ; coverage 0.885 »
Rollback → v1 (historique intact : 3 versions) ; audit : 6 entrées horodatées.
```

## 4. Portée honnête

- On gouverne des **versions de paramètres** (apprentissage de niveau 1). La **sélection de forme de
  modèle** (niveau 2 : affine vs proportionnel, saturation) et la **découverte de structure** (niveau 3 :
  nouvelles arêtes causales) restent des chantiers **distincts et d'une autre nature**.
- La garde de promotion utilise la **qualité de prédiction** (RMSE/MAE sur validation) comme proxy. La
  vraie **attribution d'impact sur les décisions** (ce nouveau modèle a-t-il amélioré les KPI métier ?)
  exige le flux de données réelles + l'imputation causale des résultats — c'est le verrou connexe.
- La dérive est mesurée sur l'erreur ; pas encore de tests statistiques formels (Page-Hinkley, ADWIN).

## 5. Où se situe désormais l'enjeu

Comme le note le fondateur : l'enjeu n'est plus l'algorithme, c'est la **qualité, la traçabilité et la
gouvernance** des connaissances apprises. Avec cette couche, HELYOS peut apprendre **sans perdre le
contrôle** : chaque évolution du modèle est justifiée, validée avant activation, réversible, et
surveillée pour la dérive. C'est la condition pour qu'un système apprenant pilote des décisions
d'entreprise en confiance.

## 6. Prochain palier

1. **Brancher le flux de données réelles** (connecteurs → journalisation exécution → `relearn` +
   `propose`) : la gouvernance ne prend toute sa valeur qu'alimentée en continu.
2. **Attribution d'impact décisionnel** : mesurer si une version améliore réellement les résultats métier.
3. Niveaux 2–3 d'apprentissage (forme, structure) — sous la même gouvernance.

Voir [[HELYOS-Learning-Loop-v1.0]], [[HELYOS-Domain-Layer-v2.0]], [[ADR-0003]] (noyau de gouvernance).
