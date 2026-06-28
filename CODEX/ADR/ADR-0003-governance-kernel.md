# ADR-0003 — La gouvernance vit dans le Kernel

- **Statut** : Accepted
- **Date** : 2026-06-28
- **Décideur(s)** : Le Conservateur
- **Principes ADN engagés** : 6, 11, 16

## Contexte

HELYOS doit agir sur le monde (fichiers, e-mails, transactions, robot). Une intelligence qui agit sans cadre est un risque. Le Codex v0.1 définit une autonomie graduée **A0–A5** et trois interdits absolus (pas de suppression sans backup, pas d'action externe sensible sans validation, pas d'auto-escalade). Où placer ce cadre ?

## Décision

La gouvernance est un **composant central du Kernel** (`governance/`), pas une couche optionnelle ni une politique « best-effort » côté agent. Concrètement :

- Toute action passe par le **PolicyEngine** avant exécution.
- Le PolicyEngine renvoie `ALLOW` / `REQUIRE_VALIDATION` / `DENY`.
- Les **règles d'or** sont codées et **testées** ([`tests/test_governance.py`](../../apps/jarvis-kernel/tests/test_governance.py)).
- Chaque décision est **journalisée** (`AuditLog`).
- Un agent **ne peut pas** modifier son propre niveau (GR-3, anti-auto-escalade).

## Conséquences

- **Positives** : éthique *exécutée* et non seulement *déclarée* ; auditabilité ; veto humain architectural.
- **Négatives / coûts** : chaque action a un léger surcoût (évaluation + journal) — accepté comme prix de la sûreté.
- **Chemin de sortie** : le moteur de politique est modulaire ; sa logique peut évoluer par RFC sans changer le contrat `ALLOW/REQUIRE_VALIDATION/DENY`.

## Alternatives écartées

- *Gouvernance déléguée aux agents* — non vérifiable, contournable, contraire à l'ADN 16.
- *Gouvernance comme middleware HTTP seulement* — insuffisant : les actions internes (agent→agent) la contourneraient.
