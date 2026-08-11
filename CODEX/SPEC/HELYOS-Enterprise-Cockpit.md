# HELYOS — Cockpit Entreprise (Front B, la vue du dirigeant)

- **Statut** : Accepted · **Date** : 2026-08-11
- **Implémentation** : `api/routes.py` (`GET /os/cockpit`) · `web/os.html` · `main.py` (front door)
- **Tests** : `test_os_cockpit.py` (3)

---

## 1. Deux fronts qui avancent ensemble

- **Front A — Intelligence / Core** : CFG, gouvernance, propriétés critiques, mutation, CI,
  mémoire, métacognition (on ne s'arrête pas).
- **Front B — Logiciel d'entreprise** : le produit que le dirigeant et les employés utilisent,
  **AI-first** (HELYOS opère par défaut) avec le **manuel en backup**.

Chaque avancée de A doit renforcer B. Ce brick ouvre B par l'écran d'accueil : le **Cockpit**.

## 2. L'écran d'accueil n'est plus un dashboard de développeur

La racine `/` redirige désormais vers `/app/os.html` (le dashboard technique reste sous `/app/`).
Le dirigeant ouvre HELYOS et voit : état global, chiffres clés, **ce qu'HELYOS fait en ce
moment**, et ce qui l'attend, lui.

## 3. Règle d'or : aucun chiffre inventé (anti « coquille vide »)

`GET /os/cockpit` assemble **uniquement du réel** :
- **Argent** ← livre de caisse (`ledger.global_summary`). Sans écriture : `0 €` + état
  **« à connecter »**, jamais un faux « 142 580 € ».
- **Pipeline / clients** ← prospection réelle. **À encaisser / commandes** ← carnet de commandes.
- **Opérations** ← ce qui tourne vraiment : Pouls, gouvernance (nombre de décisions arbitrées),
  Ingénierie/R&D (AST · propriétés critiques · couverture · diff-coverage · mutation · CI),
  portefeuille, connecteurs branchés, agents, comité C-suite.
- **En attente de toi** ← les items du Pouls (tâches humaines, connecteurs à brancher).
- **Score global** ← composite **transparent** (parts affichées) : capacités fortes,
  monétisation à activer → un score honnête (≈ 65–70), pas un 94 décoratif.

## 4. AI-first, human-backup — rendu visible

Bandeau : « HELYOS est prêt et opère, mais N action(s) dépendent de toi ; l'IA gère le reste,
tu restes l'opérateur de secours. » Un bouton **Mode manuel** est présent (bascule d'affichage ;
l'override réel viendra avec l'IAM). Le mode par défaut est **AI-first**, l'autonomie A0–A5 est
affichée. C'est la traduction produit du principe : *HELYOS est l'opérateur principal, l'humain
est le backup.*

## 5. Départements (le vrai découpage)

Cockpit · CRM & Ventes · Marketing · Finance · Administration · SAV/Customer Success ·
Operations/ERP · **Engineering/R&D** (tout Front A y vit — actif) · RH. Chaque carte porte un
état honnête (`actif` / `prêt` / `à connecter`) et pointe vers le backing réel quand il existe
(`/prospection`, `/ledger`, `/orders`, `/docs`).

## 6. Preuve

- Endpoint testé (TestClient) : structure + **honnêteté** (CA = 0 & « à connecter », le
  compteur d'opérations = le nombre réel d'items, Engineering `actif`).
- Rendu vérifié dans le navigateur : *AI OPERATOR — ONLINE*, état **67/100**, 7 opérations
  réelles, 4 tâches humaines en attente, 9 départements.
- **421 tests** verts, aucune régression du changement de front door.

## 7. Portée honnête & suite

- Les modules Marketing/SAV/RH/Admin sont pour l'instant des **cartes d'état** (« à connecter »)
  sans page dédiée — le squelette est réel, le contenu viendra département par département.
- Le **Mode manuel** est visuel ; l'override effectif + **Organization & IAM** + **SAFE MODE**
  sont le prochain jalon produit (déjà noté en mémoire : AI-first / fail-operational).
- Les chiffres deviendront « réels » à mesure que les connecteurs (banque, ERP, Stripe/Gumroad)
  se branchent : le cockpit est déjà câblé pour les afficher sans rien changer.

Voir [[HELYOS-Critical-Property-AST]], [[HELYOS-CI-Incident-Intelligence]].
