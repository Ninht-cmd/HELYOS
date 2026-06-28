# ADN HELYOS — Les 16 principes fondateurs

`v0.2` · Statut : **Stable (non négociable)** · Source canonique : Codex Foundation v0.1

---

L'ADN est le niveau d'autorité **le plus élevé** du Codex (voir [hiérarchie](../README.md)). Un principe ne se contourne pas : il se **fait évoluer par RFC**, ou il s'applique. En cas de conflit entre deux principes, le **n° le plus bas l'emporte** (la vision prime sur tout).

| # | Principe | Ce que ça veut dire concrètement |
|---|----------|----------------------------------|
| 1 | **Vision avant technologie** | On choisit un outil parce qu'il sert la vision, jamais parce qu'il est à la mode. Toute techno doit se justifier devant le Codex. |
| 2 | **Local First** | Le système fonctionne **sans Internet** pour son cœur. Le cloud est opt-in, jamais requis. La donnée appartient au Conservateur. |
| 3 | **Open Source First** | Préférer systématiquement les briques ouvertes et auto-hébergeables. Une dépendance propriétaire exige une RFC justifiée. |
| 4 | **Modularité absolue** | Chaque composant est remplaçable sans effondrer l'ensemble. Interfaces stables, implémentations jetables. |
| 5 | **Pas de dette technique volontaire** | On ne sacrifie pas le futur pour gagner une semaine. La dette *subie* se documente ; la dette *volontaire* est interdite. |
| 6 | **Tout est observable** | Logs structurés, traces, métriques par défaut. Si on ne peut pas le voir, on ne le déploie pas. |
| 7 | **Jarvis apprend** | Le système capitalise : chaque interaction enrichit la mémoire et, à terme, les compétences. |
| 8 | **Tout est mesurable** | Pas d'affirmation de valeur sans métrique. La friction supprimée se chiffre. |
| 9 | **Intelligence composée** | La puissance vient de la **composition** d'agents/outils spécialisés, pas d'un modèle unique tout-puissant. |
| 10 | **Héritage et transmission** | On documente pour ceux qui viendront. Le Codex est un legs. |
| 11 | **Complexité maîtrisée** | La complexité est un budget. On la dépense où elle crée de la valeur, jamais par confort. |
| 12 | **Construire pour les générations futures** | Décisions évaluées à l'horizon décennies, pas trimestres. |
| 13 | **Les revenus financent la recherche** | Le but du chiffre d'affaires est de **libérer la R&D**, pas l'inverse. Voir [boucle économique](../05_ECONOMIE/00_Boucle_Economique.md). |
| 14 | **Une fonctionnalité supprime une friction mesurable** | Critère d'admission de toute feature. Pas de friction supprimée → pas de feature. |
| 15 | **Relire le Codex avant toute stratégie** | Aucune décision stratégique ne démarre sans relecture du Codex concerné. |
| 16 | **Aucune décision importante ne reste dans une conversation** | Elle devient une [RFC](../RFC/README.md) ou un [ADR](../ADR/README.md). La mémoire d'un modèle n'est jamais la source de vérité. |

## Corollaires opérationnels

- **Principe d'indépendance** (de 2, 3, 9) : *aucune dépendance unique* à un fournisseur ou à un modèle. Tout LLM est derrière une abstraction (LiteLLM) et reste substituable.
- **Principe d'auditabilité** (de 6, 8) : toute action d'un agent laisse une trace exploitable *a posteriori*.
- **Principe de réversibilité** (de 4, 5) : toute décision technique doit avoir un chemin de sortie connu.

## Lien avec la gouvernance

L'ADN se **traduit en règles exécutables** dans le kernel :
- Principe 16 → toute action sensible exige une trace ([audit log](../../apps/jarvis-kernel/src/jarvis_kernel/governance/audit.py)).
- Principe 6 → observabilité par défaut.
- La [gouvernance A0–A5](../03_GOUVERNANCE/00_Autonomie_A0_A5.md) est l'application directe des principes 6, 11 et 16.

---

> *Note de réconciliation :* le Dossier Fondateur v0.1 listait une variante à 10 points. Elle est **incluse** dans ces 16 (Local First, Open Source First, modularité, revenus→R&D, réduction des frictions, temps→actifs, générations, non-dépendance). Aucun principe n'a été perdu — voir [ADR-0001](../ADR/ADR-0001-codex-source-of-truth.md).
