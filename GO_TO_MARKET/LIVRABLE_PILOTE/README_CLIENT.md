# Relance automatique des factures impayées
### Documentation d'installation et d'exploitation — livrable pilote

*Document en marque blanche : remplacer [Agence] par votre enseigne avant remise au client final.*

---

## 1. Ce que fait ce workflow

Chaque matin à 8 h, le système :
1. Lit votre feuille Google Sheets « Factures » ;
2. Identifie les factures **impayées** dont l'échéance est dépassée ;
3. Compose une relance **graduée** selon le retard :

| Niveau | Déclenchement | Ton |
|---|---|---|
| Relance 1 | J+7 après échéance | courtois, « sauf erreur de notre part » |
| Relance 2 | J+14 | ferme, propose de signaler une difficulté |
| Relance 3 | J+30 | dernier rappel avant recouvrement (amiable) |

4. Envoie l'e-mail depuis **votre** adresse (SMTP) ;
5. Trace chaque relance dans l'onglet « Journal_relances » (audit complet).

**Garde-fous intégrés** — ce qui fait la différence avec un script naïf :
- Jamais deux relances au même client à moins de 6 jours d'intervalle (anti-spam) ;
- Une facture marquée « payée » ou aux données incomplètes n'est **jamais** relancée ;
- **L'envoi est livré DÉSACTIVÉ** : vous exécutez d'abord le workflow, vous lisez
  les messages générés sur vos vraies données, et c'est vous qui activez l'envoi.

## 2. Prérequis

- Une instance n8n (cloud dès 20 €/mois, ou auto-hébergée : 0 €) ;
- Un compte Google (Sheets) ; un accès SMTP à votre messagerie
  (OVH, Gmail, Outlook — identifiants fournis par votre hébergeur de mail).

## 3. Installation (15 minutes)

1. Dans n8n : **Workflows → Import from file** → `workflow_relance_factures.json` ;
2. Créez la feuille Google Sheets avec deux onglets :
   - **Factures** — colonnes exactes :
     `client | email | numero_facture | montant_eur | date_echeance | statut | derniere_relance`
     (dates au format `AAAA-MM-JJ` ; `statut` = `payée` ou vide) ;
   - **Journal_relances** — laissez vide, il se remplit seul ;
3. Ouvrez les deux nœuds Google Sheets → connectez votre compte →
   remplacez `REMPLACER_PAR_ID_FEUILLE` par l'ID de votre feuille
   (la longue chaîne dans l'URL de la feuille) ;
4. Ouvrez « Envoi SMTP » → créez l'identifiant SMTP → mettez votre
   adresse d'expédition (`compta@votre-domaine.fr`) ;
5. **Test à blanc** : bouton *Execute Workflow* → ouvrez la sortie du nœud
   « Filtrer impayées + composer relances » → vérifiez les messages ;
6. Quand les messages vous conviennent : clic droit sur « Envoi SMTP »
   → *Enable*, puis activez le workflow (interrupteur en haut à droite).

## 4. Personnalisation courante

| Besoin | Où |
|---|---|
| Changer l'heure d'envoi | nœud « Chaque matin 8h » |
| Changer les seuils J+7/J+14/J+30 | nœud « Filtrer + composer », 3 premières lignes |
| Modifier le texte des e-mails | même nœud, bloc `corps` |
| Copie cachée comptable | nœud « Envoi SMTP » → Options → BCC |

## 5. Conformité et sécurité

- **RGPD** : les données restent dans VOS outils (votre Sheets, votre SMTP,
  votre n8n). Aucun tiers ne reçoit vos données clients. Base légale : exécution
  du contrat (recouvrement de créances liées à une prestation fournie).
- Les relances 1 à 3 restent **amiables** ; ce workflow n'engage aucune
  procédure judiciaire et ne remplace pas un conseil juridique.
- Identifiants stockés chiffrés dans n8n ; aucun mot de passe dans le workflow.

## 6. Limites connues (annoncées, pas découvertes)

- Ne lit pas les réponses des clients (une réponse « je paie vendredi »
  n'arrête pas la relance suivante : marquez `statut = accord` à la main) —
  automatisation possible en évolution ;
- Ne joint pas le PDF de la facture (évolution possible : lien vers votre
  espace de facturation) ;
- Source unique : Google Sheets (connecteurs Sellsy/Pennylane/QuickBooks : sur devis).

## 7. Support

Inclus 30 jours après livraison : corrections de dysfonctionnements et une
session de 30 min de prise en main. Évolutions : sur devis ou abonnement
maintenance (150–400 €/mois selon périmètre).

---
*Livré par [Agence] — construit et testé le [date]. Version pilote 1.0.*
