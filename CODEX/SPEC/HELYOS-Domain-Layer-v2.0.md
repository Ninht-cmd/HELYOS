# HELYOS Domain Layer v2.0 — les lobes spécialisés

- **Statut** : Accepted (framework + 2 domaines implémentés + testés) · **Date** : 2026-08-02
- **Implémentation** : `world/domains/` · **Tests** : `test_domains.py` (9) · **Étend** : Ontology v1.0, Simulation v1.3

---

## 1. Le manque comblé

Le noyau + l'ontologie donnent un **cerveau de coordination** : des entités génériques et un
Monte-Carlo. Mais 26 types génériques ne remplacent pas un ingénieur industriel + un directeur
financier. Un vrai conglomérat exige des **domaines** qui injectent leurs entités, leurs **variables**
et surtout leurs **équations** (les lois causales du métier), que le Monte-Carlo exploite.

## 2. Le framework (Domain Schema → Variables → Lois)

Un domaine est un objet `Domain` (dans `world/domains/`) qui déclare :
- `entity_types` : des types injectés **ou** l'enrichissement de types existants ;
- `equations` : des **fonctions pures, testables** (les lois du domaine).

`Ontology.extend()` **fusionne** ces types dans l'ontologie de base (ajoute un type, ou **ajoute des
attributs** à un type existant sans écraser les siens). `build_ontology(*domains)` produit l'ontologie
enrichie ; `full_ontology()` charge tous les domaines disponibles. Ajouter un lobe = ajouter un fichier,
zéro modification du noyau.

## 3. Domaines implémentés (réels, chiffrés)

### 3.1 `domains/finance.py` — lois financières
`gross_margin`, `runway_months`, `roi`, **`npv`** (VAN = Σ CF_t/(1+r)^t), **`irr`** (TRI par bissection),
`payback_period`. Injecte le type **`BusinessUnit`** (CAPEX, OPEX, revenus, coûts, marge_brute, cash,
runway, roi, risque_faillite). `wire_finance()` dérive marge brute et runway.

### 3.2 `domains/engineering.py` — lois méca & manufacturing
`bending_stress` (σ = M·c/I), `safety_factor` (limite/contrainte), `thermal_expansion` (L·α·ΔT),
**`oee`** (disponibilité×performance×qualité), `throughput` (capacité×OEE), `unit_cost`. **Enrichit**
`Machine` (oee, cycle_time, énergie, maintenance) et `Part` (contrainte_max, limite_élastique,
coef_sécurité, fatigue). `wire_machine()` / `wire_part_safety()` dérivent OEE et coefficient de sécurité.

### 3.3 Support Monte-Carlo générique
`monte_carlo_metric(graph, metric_fn, …)` : distribution d'une **métrique métier** arbitraire (VAN,
profit annuel, cadence…) + P(métrique < 0), là où `monte_carlo` ne donnait que l'utilité.

## 4. Preuve — usine de robots (l'exemple du fondateur)

```
ENGINEERING  OEE = 82.9%   cadence = 663 pièces/mois   coef. sécurité = 2.78 (250/90 MPa)
FINANCE      marge brute = 38.5%   runway = 10 mois   VAN(10%,5a) = 987 236 €   TRI = 199%   ROI = 900%
MONTE-CARLO  profit annuel : médiane 266 k€  [P5 103 k€ .. P95 366 k€]   P(année déficitaire) = 0.1%
             (avec événement « acier +30% », p=0.35)
```

Le Monte-Carlo devient réellement puissant : chaque futur combine l'incertitude des lois financières
ET industrielles, avec des chocs stochastiques.

## 5. Portée honnête (crucial)

- **HELYOS n'est pas** SAP + CATIA + Bloomberg + ERP. Ces domaines apportent les **lois réutilisables**
  (finance, méca, manufacturing) exploitées par la décision et le Monte-Carlo — pas la profondeur d'un
  logiciel métier dédié (pas de vrai solveur FEM, pas de moteur comptable complet, pas de flux d'ordres).
- **2 domaines** sont réellement implémentés (**finance**, **engineering/manufacturing**). Les autres —
  **supply_chain**, **trading**, **market** — ont l'**interface prête** (même patron `Domain`) mais leurs
  équations restent à écrire. Ce sont des fichiers à ajouter, pas une refonte.
- Les équations sont **exactes mais réduites** (VAN/TRI/OEE/contrainte de flexion standard) ; elles ne
  couvrent pas encore fatigue avancée, fiscalité multi-juridiction, couverture de change, etc.

## 6. Roadmap des domaines

| Domaine | Statut |
|---|---|
| Finance OS | 🟢 socle (VAN, TRI, ROI, runway, marge) · à étendre : fiscalité, valorisation, change |
| Engineering/Manufacturing OS | 🟢 socle (contrainte, sécurité, OEE, cadence, coût unitaire) · à étendre : FEM, thermique, fatigue |
| Supply Chain OS | ⬜ interface prête (lead time, MOQ, capacité, risque dépendance) |
| Trading OS | ⬜ interface prête (portfolio, VaR, backtest) — au-delà de RSI/SMA actuels |
| Market OS | ⬜ interface prête (demande, élasticité-prix, part de marché) |

**Prochain palier recommandé** : **v1.4 Opportunity Engine** (Business Factory) — générer des
`Opportunity`, les simuler via v1.3 avec les lois de domaine, classer par espérance/risque, proposer la
création. Toutes les briques sont désormais sous la main.

Voir [[HELYOS-Simulation-Engine-v1.3]], [[HELYOS-Reality-Layer-v1.1]], [[HELYOS-Ontology-v1.0]].
