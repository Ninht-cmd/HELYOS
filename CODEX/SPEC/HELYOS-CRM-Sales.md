# HELYOS — CRM / Sales réel (le premier département pleinement opérationnel)

- **Statut** : Accepted · **Date** : 2026-08-29
- **Implémentation** : `business/crm.py` · `integrations/system_registry.py` · endpoints `/os/crm*`
- **Tests** : `test_crm.py` (4 : boucle end-to-end, scope IAM, agent suspendu, qualification)

---

## 1. La boucle, gouvernée de bout en bout

```
lead réel → stocké → Sales Agent le lit (scope IAM) → qualification → opportunité
→ e-mail préparé → GOUVERNANCE (envoi = GR-2, jamais autonome) → envoi validé
→ réponse → CRM mis à jour → vente → Outcome → Mémoire
```

Chaque étape passe par l'**IAM** (identité/périmètre/permission), puis l'**exploitation** (un agent
`SUSPENDED` est bloqué) et la **gouvernance** (GR-x). Réutilise `ProspectionPipeline` pour le
stockage des prospects — **aucun doublon**.

## 2. Zéro coquille vide : ACTIVE seulement si la boucle tourne

`crm_sales` reste **DEGRADED** tant qu'aucun **Outcome** n'a bouclé. Dès qu'un lead va jusqu'à la
vente (Outcome enregistré), il passe **ACTIVE**. Prouvé en direct :

```
crm_sales AVANT la boucle : DEGRADED
  qualif « Café Lumière » : 100 → qualified
  envoi sans validation    : REQUIRE_VALIDATION (GR-2)
  envoi validé             : ALLOW
  clôture (gagné 490 €)    : Outcome observed=1.0
  snapshot : 1 opportunité · 1 gagnée · 490 €
crm_sales APRÈS la boucle : ACTIVE
```

La vente alimente le **carnet de commandes** (`à encaisser`) → flux réel jusqu'au cockpit.

## 3. Scope IAM & sécurité (tests)

- `sales_agent` (rôle Sales) : ingest/qualify/prepare/send **ALLOW** ; l'envoi externe passe en
  **GR-2** (REQUIRE_VALIDATION) sans validation humaine.
- `finance_agent` (rôle Finance, pas de `crm.update`) → **DENY IAM-RBAC**.
- `sales_agent` **SUSPENDED** (SAFE MODE scopé) → envoi **DENY OPS-SUSPENDED** même avec la
  permission IAM (l'exploitation prime).

## 4. Qualification honnête

Score déterministe 0–100 (contact, entreprise, mots-clés d'intention, lead nommé) → `qualified /
to_nurture / low`. Pas une boîte noire ; l'e-mail est rédigé par le LLM local (Ollama) avec repli
gabarit. **Rien n'est envoyé sans validation** (GR-2).

## 5. Endpoints

`GET /os/crm` (état réel) · `POST /os/crm/lead` (ingest + qualification, scope IAM) ·
`POST /os/crm/send` (prépare + GR-2) · `POST /os/crm/close` (Outcome + vente). Câblé au
BrickRegistry (`crm_sales`) et au cockpit.

## 6. Portée honnête & suite

- **Réel** : boucle gouvernée, scope IAM, qualification, Outcome→mémoire, vente→commandes.
- **v1.1** : ingestion de leads depuis l'extérieur (formulaire/connecteur), envoi e-mail effectif
  (connecteur SMTP — aujourd'hui `à connecter`), et le **lien d'apprentissage** complet (Outcome
  du sales_agent → calibration, comme le dev_agent) est amorcé (Outcome stocké) mais pas encore
  rebouclé sur la confiance composite.
- **Front A / CFG interprocédural** (prochain, en parallèle) prouvera structurellement qu'aucun
  chemin `CRM → email/paiement` ne contourne `IAM → Operations → Governance`.
- **Encaissement** : `payment_connector` reste `MISSING` — la vente produit un « à encaisser »
  réel, mais le canal de paiement (Stripe/Gumroad) manque encore.

Voir [[HELYOS-IAM]], [[HELYOS-Operations-SafeMode]], [[HELYOS-System-Registry]].
