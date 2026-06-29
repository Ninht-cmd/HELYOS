# Business Model — Open Core

`v0.3` · Statut : **Adopté** ([ADR-0008](../ADR/ADR-0008-open-core-business-model.md)) · Cible : **~100 000 €/mois**

---

> Un projet de recherche ambitieux **et** une entreprise durable. Le modèle finance la R&D
> sans fermer le cœur — application directe de la [boucle économique](00_Boucle_Economique.md)
> (Recherche → Produits → Revenus → Patrimoine → Recherche).

## Le moat (ce qui rend le modèle défendable)

L'**actif le plus précieux** d'HELYOS n'est pas le code en soi, c'est **la gouvernance + la
mémoire + les agents spécialisés + (à terme) les données/modèles**. Or la gouvernance, pour
inspirer confiance, **doit être auditable** → donc ouverte. Le paradoxe se résout ainsi :

- **On ouvre la gouvernance** (c'est un argument de vente, pas une faiblesse).
- **On vend la capacité de l'exploiter à l'échelle, en confiance, dans des domaines régulés.**

> **Le wedge :** les secteurs **régulés** (finance, juridique, santé, industrie) ont besoin d'IA
> **auditable et gouvernée**. La gouvernance A0–A5 + l'audit immuable d'HELYOS est exactement
> ce qu'ils ne trouvent pas chez les assistants « boîte noire ». **Notre différenciateur technique
> est aussi notre argument commercial premium.**

## Les trois sources de revenus

| Source | Quoi | Pour qui |
|--------|------|----------|
| **1. Licence commerciale** (dual-licensing AGPL) | Exemption à l'AGPL pour intégration propriétaire | Éditeurs/entreprises qui ne peuvent pas rouvrir leur code |
| **2. Modules Pro / Enterprise** | Agents spécialisés, mémoire distribuée, orchestration multi-IA, dashboard, déploiement 1-clic | Équipes & entreprises |
| **3. SaaS / Cloud géré** | HELYOS hébergé + support & MAJ prioritaires + SLA | Ceux qui ne veulent pas auto-héberger |

## Paliers d'offre

| Offre | Prix indicatif | Contenu | Licence |
|-------|----------------|---------|:-------:|
| **Community** | **0 €** (auto-hébergé) | Cœur complet : kernel, gouvernance, API, SDK, mémoire de base | AGPL-3.0 |
| **Pro** (self-serve) | **~49–99 €/mois** /siège | Mémoire avancée, quelques agents spécialisés, MAJ prioritaires | Commerciale |
| **Team / Cloud** | **~299–999 €/mois** | SaaS hébergé, orchestration multi-IA, dashboard équipe | Commerciale |
| **Enterprise** | **~2 000–15 000 €/mois** | Agents métier (juridique/finance/industrie), 1-clic, SLA, licence commerciale, support dédié | Commerciale |

## Chemin vers 100 000 €/mois (~1,2 M€ ARR)

Plusieurs compositions atteignent la cible — la réalité sera un mélange :

| Scénario | Pro | Team/Cloud | Enterprise | Total/mois |
|----------|-----|-----------|------------|:----------:|
| **A — PLG** (bottom-up) | 600 × 80 € = 48 k | 80 × 500 € = 40 k | 4 × 3 k = 12 k | **100 k€** |
| **B — Enterprise** (top-down) | 200 × 80 € = 16 k | 30 × 600 € = 18 k | 12 × 5,5 k = 66 k | **100 k€** |

> Le scénario **B** (peu de gros contrats régulés) demande **moins de clients** et exploite le
> wedge gouvernance → c'est le **chemin à plus fort levier** pour HELYOS. Le scénario A construit
> la notoriété et le funnel. On vise un **mélange**, en démarrant par A pour amorcer l'adoption.

## La montée en 3 paliers (la cible 100 k n'est pas le point de départ)

| Palier | Revenu/mois | Offre activée | Structure |
|:------:|:-----------:|---------------|-----------|
| **1** | ~5 000 € | Pro self-serve uniquement | Solo (le Conservateur). Valider la disposition à payer. |
| **2** | ~20 000 € | + Cloud SaaS + 1ʳˢ contrats Enterprise | Mini-équipe (support, infra, facturation). |
| **3** | ~100 000 € | + Modules Enterprise + licence commerciale + motion commerciale | Équipe + ventes + conformité. Trajectoire startup. |

## Métriques à suivre (ADN 8 & 14)

- **Adoption** : étoiles/forks, installations du cœur, agents communautaires.
- **Conversion** : Community → Pro → Team → Enterprise (taux & délai).
- **Revenu** : MRR, ARPU par palier, churn, LTV/CAC.
- **R&D financée** : part du MRR réinvestie en recherche (cible : majoritaire, ADN 13).

## Garde-fous (cohérence ADN)

- **Le cœur reste ouvert et auditable** — on ne « referme » jamais ce qui est publié.
- **GR-7** : aucune fonctionnalité financière autonome, même côté produit.
- **Frontière nette** open/Pro : [02_Frontiere_Open_Core](02_Frontiere_Open_Core.md).
- **La recherche reste le but** ; les revenus la financent, pas l'inverse (ADN 13).

> *Note :* chiffres **illustratifs** (cibles de modélisation), pas des promesses. À réviser par RFC
> à mesure que les données réelles arrivent.
