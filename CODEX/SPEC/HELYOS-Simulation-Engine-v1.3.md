# HELYOS Simulation Engine v1.3 — d'une trajectoire à une distribution de futurs

- **Statut** : Accepted (moteur implémenté + testé) · **Date** : 2026-08-02
- **Implémentation** : `world/simulation.py` · **Tests** : `test_simulation.py` (6) · **Étend** : Reality Layer v1.1
- **Franchit** : H=1 → « N futurs → distribution → risque → décision ». C'est le vrai saut.

---

## 1. Le problème que ça résout

Jusqu'ici : `action → trajectoire unique → choix`. Le monde réel produit une **distribution** de
résultats. v1.3 répond à : *« Quelle histoire survit aux futurs probables, compte tenu de mon appétit
au risque ? »* — en tirant N futurs, en agrégeant une distribution d'utilité, et en décidant sur
**espérance ET risque**, jamais sur une moyenne seule.

## 2. Les cinq briques (réelles, testées, chiffrées)

**1. Monte-Carlo World Simulator** — `monte_carlo(graph, company, plan, now, n, seed)`. Chaque futur :
échantillonne les croyances de base `N(μ,σ)` (bornées par nature), re-dérive la chaîne causale, applique
le plan puis les événements, mesure l'utilité. Reproductible (graine).

**2. Stochastic Events** — `StochasticEvent(name, probability, interventions, op)`. Un événement se
**produit avec une probabilité** ; s'il tire, il frappe le monde (mul/set/add). Ordre réaliste : on
**déploie le plan**, *puis* le monde frappe.

**3. Risk Engine** — la distribution donne `E[U]`, `σ`, `P(faillite)`, `P(succès)`, `CVaR 5%`, percentiles
P5/P50/P95. Score ajusté au risque : `score = E[U] − λ·σ`, où **λ (aversion) vient de la tolérance au
risque de l'objectif**.

**4. Trajectory Ranking** — `rank_trajectories(plans, …)` : classe des **histoires** (suites d'actions +
événements) par score ajusté au risque. **Garde-fou v1.2** : `feasible_resources` écarte tout plan dont
les ressources — *par ressource précise*, pas par catégorie grossière — sont insuffisantes. Pas de
simulation de projet impossible.

**5. Apprentissage causal (amorce)** — `learn_elasticity(pairs)` : ajuste un coefficient causal par MCO
sur des couples (cause, effet) observés. Première brique pour remplacer un coefficient écrit à la main
par un coefficient **appris des résultats réels**.

## 3. Preuve (l'exemple du fondateur, chiffré)

```
MONTE-CARLO (4000 futurs / plan)
  A · gros pari :  E[U]=+0.276  σ=0.113  P(faillite)=42%  P5..P95=[+0.12 .. +0.40]
  B · prudent   :  E[U]=+0.227  σ=0.029  P(faillite)= 5%  P5..P95=[+0.17 .. +0.27]

RISK ENGINE (même question, choix inversé selon l'objectif)
  Objectif AGRESSIF (λ=0.2) →  1. A (+0.253)   2. B (+0.222)
  Objectif PRUDENT  (λ=3.0) →  1. B (+0.142)   2. A (−0.062)
  Plan « usine robotique » (4 ingénieurs IA, 1 dispo) →  ÉCARTÉ (manque 3)  ← garde-fou ressources

APPRENTISSAGE CAUSAL
  8 observations bruitées (prix, coût) → loi apprise : coût ≈ 1.578·prix (R²=0.98 ; vérité 1.6)
```

## 4. Positionnement roadmap (statut honnête)

| Palier | Statut |
|---|---|
| **v1.2 Intelligence Structure** — Resource Graph granulaire, faisabilité par ressource | ✅ **Fait** (garde-fou). Action Ontology / Process Engine complets = à venir. |
| **v1.3 Simulation** — Monte-Carlo, Stochastic Events, Risk Engine, Trajectory Ranking | ✅ **Fait**. |
| **v1.3 Learning causal** — apprendre les lois du monde | 🟡 **Amorce** : coefficient d'une arête appris (MCO). Cf. §5. |
| **v1.4 Opportunity Engine** | ⬜ à venir |
| **v2.0 Domain OS** (Finance/Trading/Engineering…) | ⬜ à venir |

## 5. Ce que v1.3 N'EST PAS (annoncé)

- L'apprentissage causal se limite à **ajuster un coefficient** d'une relation **déjà posée** ; il ne
  **découvre pas la structure** (quelles arêtes existent) et n'est **pas encore branché** pour mettre à
  jour automatiquement les dérivations du graphe à partir de résultats réels (chantier v1.2/1.3 suivant).
- Les événements stochastiques et leurs impacts sont **spécifiés à la main** (pas encore estimés d'un
  historique).
- `company_utility` reste une scalarisation heuristique par entité, non calibrée sur des résultats.
- Le simulateur échantillonne des **gaussiennes indépendantes** (pas de corrélations ni de lois
  non gaussiennes — cf. Phase E DD-0001).

## 6. Prochain palier

1. **Boucler l'apprentissage** : après exécution réelle d'un plan, journaliser (cause → effet) et appeler
   `learn_elasticity` pour **mettre à jour la dérivation** du graphe → le monde s'auto-corrige.
2. **v1.4 Opportunity Engine** : générer des `Opportunity`, les simuler (v1.3) et classer par
   espérance/risque → la Business Factory.

Voir [[HELYOS-Reality-Layer-v1.1]], [[HELYOS-Ontology-v1.0]], [[DD-0001]].
