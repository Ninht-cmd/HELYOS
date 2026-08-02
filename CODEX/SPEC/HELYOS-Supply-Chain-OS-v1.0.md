# HELYOS Supply Chain OS v1.0 — un Domain OS complet comme modèle scientifique gouverné

- **Statut** : Accepted (bout en bout, implémenté + testé) · **Date** : 2026-08-02
- **Implémentation** : `world/domains/supply_chain.py` · **Tests** : `test_supply_chain.py` (6)
- **Objet** : démontrer la **valeur opérationnelle** de l'architecture sur **un** domaine complet, plutôt
  que multiplier des domaines partiels — traité comme un **modèle scientifique gouverné**.

---

## 1. Le cadrage adopté

Un Domain OS n'est pas « du code à remplir » : c'est un **artefact scientifique gouverné** =
ontologie spécialisée + variables + lois/équations + distributions d'incertitude + jeux de validation +
données de calibration + historique de versions + gouvernance (promotion, rollback, dérive). Le Supply
Chain OS est construit exactement ainsi.

## 2. Couverture de bout en bout (les 8 points)

| # | Besoin | Réalisation |
|---|---|---|
| 1 | Fournisseurs & contrats | entités `Supplier` (délai moyen/σ, fiabilité), `Contract` (Reality Layer) |
| 2 | Stocks | `Stock` + **science des stocks** : SS, point de commande, EOQ, fill rate, coût total |
| 3 | Capacité de production | `Capacity` + `capacity_utilization` |
| 4 | Délais & contraintes logistiques | délai **stochastique** (σ_DLT), `Shipment` (transport, retard) |
| 5 | Événements (rupture, hausse, retard) | `StochasticEvent` (Simulation v1.3) |
| 6 | Simulation Monte-Carlo | `simulate_service_level` — vérifie qu'un point de commande **tient** |
| 7 | Apprentissage sur performances | délai réel appris des réceptions (`CausalLaw`) |
| 8 | Gouvernance des lois apprises | versions, validation avant activation, dérive (`ModelRegistry`) |

## 3. La science (exacte, validée)

`lead_time_demand_std` (σ_DLT = √(LT·σ_d² + d²·σ_LT²)), `service_level_z`, `safety_stock`,
`reorder_point`, `eoq` (Wilson), `normal_loss` (L(z)=φ(z)−z(1−Φ(z))), `expected_shortage`, `fill_rate`,
`total_inventory_cost`, `capacity_utilization`. **4/4 cas de référence validés** (EOQ, L(z), SS).

## 4. Preuve — de bout en bout (chiffré, testé)

```
[1-4] Politique (demande 10/j σ2, délai 9j σ1, service 95%) :
      σ_DLT 11.66 · stock sécurité 19.2u · point de commande 109.2u · EOQ 427u · fill rate 99.9% · coût 934€/an
[3]   Capacité : utilisation 83% (demande 10/j vs 12/j)
[6]   Monte-Carlo (20 000 cycles) : service atteint 95.1% (cible 95%) — le point de commande TIENT
[5-7] Fournisseur dégradé (9j→14j) : délai APPRIS 13.76j (±0.14) sur 120 réceptions
      → nouvelle politique : point de commande 109 → 158u (on recommande plus tôt)
[8]   Gouvernance : challenger PROMU (RMSE 5.08 → 1.44), v2 active (délai 13.8j)
```

Une boucle réelle : la réalité (délais qui s'allongent) modifie le modèle appris, qui — sous
gouvernance — change la décision opérationnelle (commander plus tôt).

## 5. Portée honnête

- La science des stocks couverte est **standard et correcte** mais **mono-échelon, mono-fournisseur,
  demande normale**. Le réel ajoute : multi-échelon, fournisseurs multiples & allocation, incoterms &
  douanes, contraintes de planning/capacité fines (théorie des contraintes), demande non-normale &
  saisonnalité, MOQ & remises quantité.
- **Valeur opérationnelle = données réelles.** Le domaine est démontré sur des données simulées ; sa
  vraie valeur exige un **flux réel** (réceptions, ventes, ruptures) — c'est le branchement connecteurs.
- Les difficultés propres au domaine demeurent : validation métier par des experts, qualité des données,
  cas limites, réglementation, performances numériques (le noyau les **réduit**, ne les **supprime pas**).

## 6. Ce que ça démontre

Le patron « Domain OS = modèle scientifique gouverné » **fonctionne de bout en bout** sur un domaine
complet : ontologie → lois exactes → incertitude → Monte-Carlo → apprentissage → gouvernance, produisant
une **décision opérationnelle** (quand/combien commander) qui **s'adapte au réel**. Une réussite sur un
domaine complet vaut mieux que dix domaines partiels — et celle-ci est prête à recevoir des données réelles.

Voir [[HELYOS-Domain-Layer-v2.0]], [[HELYOS-Simulation-Engine-v1.3]], [[HELYOS-Learning-Loop-v1.0]],
[[HELYOS-Model-Governance-v1.0]].
