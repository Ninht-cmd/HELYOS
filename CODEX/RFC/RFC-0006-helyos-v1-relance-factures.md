# RFC-0006 — HELYOS v1 : agent de relance de factures (1ʳᵉ tâche payante)

- **Statut** : Accepted
- **Date** : 2026-07-05
- **Auteur** : Le Conservateur
- **Principes ADN engagés** : 8, 11, 14, 16

## Résumé

Le premier agent HELYOS qui automatise **une seule tâche administrative payante** :
rédiger des relances de factures impayées, en local, sans coût d'API, gouverné.

## Problème / friction

Les commerçants/artisans perdent du temps (et du cash) sur les relances de factures.
Tâche répétitive, à fort ROI mesurable (montant récupéré). Cible du brief fondateur : *un
agent à la fois, fiabilisé, rentable, puis étendre*.

## Proposition

`agents/invoice_reminder.py` :
- `draft_reminders(invoices)` → une relance par facture, **ton escaladé** selon le retard
  (courtois ≤15 j, ferme ≤45 j, dernier rappel >45 j), rédigée via `LLMPort` (Ollama en réel,
  StubLLM en test). Niveau **A1** (préparation, aucun envoi).
- `propose_send(reminder)` → **action externe sensible** → **GR-2 : validation humaine
  obligatoire, même en A5**. HELYOS rédige ; l'humain relit et valide l'envoi.

## Décision d'architecture (« ne pas recoder ce qui existe »)

Construit **sur le kernel HELYOS** (orchestrateur + agents + Ollama + mémoire déjà en place),
**pas** sur une nouvelle stack n8n+LangGraph+NocoDB : ce serait recréer par l'infra un
orchestrateur qu'on a déjà, pour un seul agent (contraire à ADN 11 / au brief « ne pas tout
lancer d'un coup »). n8n/NocoDB viendront quand il faudra des **déclencheurs externes** (lire
une boîte mail, base no-code) — et on **vérifiera leurs licences** (n8n = Sustainable Use,
NocoDB = AGPL → impact si revente d'un SaaS).

## Gouvernance & honnêteté

- Rédaction = A1 (aucun effet monde). Envoi = A2 gouverné (GR-2). Le kernel garantit qu'aucune
  relance ne part sans validation humaine.
- `dernier_rappel` ≠ mise en demeure : **jamais** d'envoi juridique automatique ; l'humain valide.
- **Zéro client au départ = risque n°1** (le brief le dit). v1 = **démo sur données d'exemple**
  pour **valider la demande** auprès de 3-5 prospects **avant** d'investir plus.

## Prochaines étapes (séquencées, brief)

1. Montrer la démo → décrocher le 1ᵉʳ client dans une niche étroite. **Encaisser avant d'étendre.**
2. Brancher l'**envoi SMTP** derrière la gouvernance (A2) → « rédigé + envoyé après validation ».
3. Entrée réelle : CSV / NocoDB des factures impayées.
4. Seulement ensuite : 2ᵉ tâche admin (réponses clients / RDV).

## Alternatives

- *Cloner et lancer les 40 repos du brief d'un coup* — rejeté : contraire à « un agent à la
  fois » et à un capital de 0-200 €. On assemble au fil du besoin, licences vérifiées.
