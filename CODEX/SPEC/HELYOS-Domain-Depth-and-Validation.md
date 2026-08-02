# HELYOS — Profondeur de domaine & validation (preuve de scalabilité)

- **Statut** : Accepted · **Date** : 2026-08-02
- **Implémentation** : `world/domains/trading.py` + `validate_domain` · **Tests** : `test_trading.py` (9)
- **Objet** : prouver que le framework de domaines accueille une **profondeur métier de niveau
  professionnel** (pas juste Position/Asset/Market), et fournir le **harnais de validation** qui rend
  cette profondeur digne de confiance.

---

## 1. Le constat (juste) auquel ce document répond

HELYOS est un **kernel / framework cognitif** : world model, ontologie extensible, décision, simulation,
gouvernance, apprentissage, domaines branchables. C'est **l'infrastructure (~10–20 %)**. Les **80–90 %**
restants sont la **connaissance métier** des Domain OS : des centaines d'entités, des milliers de
variables, des centaines d'équations, des règles, des connecteurs, des jeux de validation, des
calibrations sur cas réels. On ne prétend pas les avoir écrits. On prouve que le kernel les **accueille**.

## 2. La preuve — un domaine Trading de profondeur professionnelle

`domains/trading.py` (Python pur, stdlib) apporte de **vraies** lois quant, pas des maquettes :

- **Options** : Black-Scholes (call/put) + **Greeks complets** — Δ, Γ, Vega, Θ, Rho.
- **Risque de marché** : VaR **paramétrique** et **historique**, **Expected Shortfall** (CVaR),
  **ratio de Sharpe**, **volatilité de portefeuille** (covariance), **bêta**.
- **Gaussiennes** : CDF, PDF, quantile (`norm_ppf`, approximation d'Acklam) — sans dépendance externe.
- **Entités injectées** : `Option` (strike, vol implicite, prix, Greeks), `Asset` (vol réalisée, bêta),
  `Portfolio` (VaR, ES, Sharpe).

**Vérifié contre le manuel** (S=K=100, r=5 %, σ=20 %, T=1 an) :
```
Call BS = 10.4506   Put = 5.5735   (parité put-call exacte)
Greeks  : Δ 0.6368   Γ 0.01876   Vega 37.52   Θ −6.41/an   Rho 53.23
VaR 95% = 1.645σ     Expected Shortfall = 2.063σ   (valeurs gaussiennes exactes)
```

## 3. Le harnais de validation de domaine

Chaque `Domain` embarque des **cas de référence** (`reference_cases` : entrées → valeur connue).
`validate_domain(domain)` exécute chaque équation et vérifie qu'elle **reproduit la valeur de manuel/norme**.

```
trading : 4/4 lois validées
  [OK] black_scholes   attendu 10.4506  obtenu 10.450584
  [OK] black_scholes   attendu 5.5735   obtenu 5.573526
  [OK] parametric_var  attendu 1.6449   obtenu 1.644854
  [OK] parametric_es   attendu 2.0627   obtenu 2.062713
```

C'est exactement la « **validation set** » au niveau des lois que réclame la construction de domaines
fiables : **la condition pour faire confiance à un domaine avant de l'alimenter en données réelles** et
de le laisser influencer des décisions. Il se compose avec la Model Governance (une loi n'est promue que
si elle valide **et** améliore la métrique).

## 4. Portée honnête

- Ceci est **une tranche profonde d'un domaine**, pas le domaine complet. Un système de trading pro exige
  encore : carnet d'ordres, profondeur de marché, **surface de vol implicite**, régimes de marché,
  financement, coûts de transaction, slippage… — le gros du 80–90 %.
- De même, remplacer un **ERP / CAO / PLM / MES** demande la même profondeur pour finance,
  manufacturing, supply chain, ingénierie (FEM, normes ISO, gammes, nomenclatures…).
- La valeur future d'HELYOS dépendra donc surtout de la **richesse des domaines**, de la **qualité des
  données réelles** qui les alimentent, et de leur **validation sur cas d'usage concrets** — ce que ce
  harnais outille, mais ne remplit pas à lui seul.

## 5. Ce que ça établit

Le patron « un domaine = un package de connaissance branché, validé, sans toucher au noyau » **tient à
une profondeur professionnelle** : 3 domaines réels (finance, engineering, **trading quant**),
équations exactes, validées contre référence. Construire les 80–90 % restants est un **travail de
contenu**, systématisé (schéma d'entités → variables → équations → cas de validation → calibration),
plus une **réécriture d'architecture**.

Voir [[HELYOS-Domain-Layer-v2.0]], [[HELYOS-Model-Governance-v1.0]], [[HELYOS-Simulation-Engine-v1.3]].
