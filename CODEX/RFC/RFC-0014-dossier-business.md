# RFC-0014 — Le Dossier Business : gérer de A à Z, une couche à la fois

- **Statut** : Accepted
- **Date** : 2026-07-11
- **Auteur** : Le Conservateur
- **Principes ADN engagés** : 8 (honnêteté), 11 (un pas à la fois), 16 (revenu d'abord)

## Le problème

« On veut gérer des business de A à Z sous tous leurs aspects. » Le portefeuille
n'était qu'une carte de statut — « trop léger » est le bon verdict. Gérer, c'est :
savoir ce qui entre et sort (caisse), ce qui échoit (dates), qui doit quoi (clients),
et pouvoir rendre un bilan à la demande.

## Décisions

### 1. Le livre de caisse (`business/ledger.py`)

Écritures append-only par business (recette | depense, montant, libellé, horodatage).
**Le CA affiché partout devient LA SOMME DES ÉCRITURES** — plus jamais une métrique
posée à la main. `encaisse 350 € — services` dans le chat, `POST /ledger` par l'API,
bilan global + par business, événement `ledger.entry` sur le bus.

Frontières, sans ambiguïté :
- **Comptabilité de caisse de PILOTAGE, pas une compta légale** (pas de TVA, pas
  d'amortissements). L'expert-comptable reste obligatoire ; ce livre le nourrit.
- **Noter ≠ exécuter** : enregistrer un paiement déjà reçu = bookkeeping interne
  (précédent : pointage de tâches). EFFECTUER un paiement reste GR-7 — testé :
  « fais un virement » exige toujours validation.
- Rattachement explicite : si le business n'est pas identifiable dans la phrase,
  HELYOS **demande** au lieu de deviner (une écriture mal rattachée est un mensonge).

### 2. Les échéances datées (`due` sur les tâches)

`add_task(..., due="AAAA-MM-JJ")` (URSSAF, TVA, renouvellements). Le Pouls signale
en URGENT toute échéance sous 7 jours, et une caisse négative sans attendre le vendredi.

### 3. La carte A→Z (état honnête, révisée à chaque RFC)

| Fonction | État |
|---|---|
| Créer / Vendre / Recouvrer / Piloter / Gouverner / Simuler | ✅ socle testé |
| **Caisse + échéances** | ✅ **cette RFC** |
| Encaissement réel (Stripe), juridique (Pro), compta légale, marketing ops, RH | 🟡/❌ chantiers |

**Loi de construction (RFC-0008)** : chaque fonction suivante devient réelle quand
un client la paie. Le premier pilote vendu inaugurera le livre de caisse avec une
écriture RÉELLE — c'est l'écriture qui vaut toutes les démos.
