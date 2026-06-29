# ADR-0009 — Conformité légale & propriété intellectuelle

- **Statut** : Accepted
- **Date** : 2026-06-29
- **Décideur(s)** : Le Conservateur
- **Principes ADN engagés** : 3, 5, 10, 16

## Contexte

HELYOS devient un produit commercial open-core. Plusieurs risques juridiques peuvent
entraîner **plagiat allégué, contrefaçon ou amendes** : noms de marque, mélange de licences,
absence de CLA, responsabilité des agents métier, RGPD. (Ceci n'est pas un avis juridique —
[09_LEGAL](../09_LEGAL/00_Conformite_IP.md).)

## Décision

1. **Marque « Jarvis » abandonnée pour l'usage public/commercial** (risque Marvel/Disney ;
   précédent NVIDIA→Riva). Conservée au plus comme **nom de code interne**. Arbitrage du nom
   produit via [RFC-0003](../RFC/RFC-0003-arbitrage-du-nom.md), **avant** toute communication.
2. **CLA obligatoire** pour toute contribution externe au cœur (préserve la propriété du
   copyright, condition *sine qua non* du dual-licensing / des modules Pro).
3. **Hygiène des licences** : un **ADR par nouvelle dépendance** ; **aucun code copyleft tiers
   dans les modules propriétaires** ; [`THIRD_PARTY_NOTICES`](../../THIRD_PARTY_NOTICES.md) tenu à jour.
4. **Disclaimers obligatoires** sur tout agent métier (juridique/finance/santé) : aide
   informative, pas un avis professionnel. Implémenté dans les agents Pro.
5. **RGPD by design** pour helyos-cloud : rien d'hébergé sans base légale, DPA, droits, UE.
6. **Originalité** : code écrit pour le projet ; seul texte verbatim = licence AGPL (autorisé FSF).

## Conséquences

- **Positives** : réduction matérielle du risque d'amende/poursuite ; modèle Pro juridiquement
  solide (copyright maîtrisé) ; confiance accrue (régulés).
- **Négatives / coûts** : friction sur les contributions (CLA) ; discipline de suivi des licences ;
  probable renommage produit (coût de marque) — mais bien moins cher qu'un litige.
- **Chemin de sortie** : décisions révisables par ADR ; le renommage est plus coûteux plus tard
  (d'où : trancher tôt).

## Alternatives écartées

- *Ignorer le risque « Jarvis »* — exposition à une mise en demeure / amende.
- *Accepter des contributions sans CLA* — casse juridiquement le modèle Pro.
- *Agents métier sans disclaimer* — responsabilité directe engagée.
