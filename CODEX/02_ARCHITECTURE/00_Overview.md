# Architecture HELYOS — Vue d'ensemble

`v0.2` · Statut : **En construction (enrichi par RFC)** · Modèle : [C4](https://c4model.com/)

---

## Principe directeur

L'architecture matérialise l'[ADN](../01_ADN/00_ADN.md) : **modulaire** (4), **locale d'abord** (2), **observable** (6), **composée** (9). Elle se lit en couches C4, du plus abstrait au plus concret :

| Niveau C4 | Question | Document |
|-----------|----------|----------|
| **1 — Contexte** | Qui utilise HELYOS, avec quoi il parle ? | [01_C4_Context.md](01_C4_Context.md) |
| **2 — Conteneurs** | Quels processus/services déployables ? | [02_C4_Containers.md](02_C4_Containers.md) |
| **3 — Composants** | Quoi à l'intérieur du Kernel Jarvis ? | [03_C4_Components_Kernel.md](03_C4_Components_Kernel.md) |
| **— Produit** | Qu'est-ce que Jarvis, sous-systèmes ? | [04_Jarvis.md](04_Jarvis.md) |

## L'arbre HELYOS (rappel du Codex)

```
HELYOS
 ├─ HELYOS OS          ← la fondation (orchestration, gouvernance, observabilité)
 ├─ Jarvis             ← le produit : l'intelligence opérationnelle
 │   ├─ Voice          ← entrée/sortie vocale
 │   ├─ Vision         ← perception visuelle (MediaPipe, OpenCV)
 │   ├─ Memory         ← mémoire court & long terme (Postgres + Qdrant)
 │   ├─ Business       ← agents métier (trading, contenu, ops)
 │   ├─ Research       ← agents de recherche & veille
 │   ├─ Robotics       ← interface robotique / edge
 │   └─ Kernel         ← le cœur : bus, gouvernance, registre, mémoire
 ├─ HELYOS Labs        ← prototypes & expérimentations
 ├─ HELYOS Research    ← R&D long terme
 └─ HELYOS Ventures    ← produits monétisables (financent la R&D)
```

## L'équation de Jarvis

> **Jarvis = Kernel + Mémoire + Agents + Outils + Gouvernance + Observabilité.**

Chacun de ces six termes est un **composant remplaçable** derrière une interface. C'est ce qui rend l'ensemble durable : on peut changer le moteur LLM, la base vectorielle ou le bus sans réécrire Jarvis.

## Décisions structurantes liées

- [ADR-0001](../ADR/ADR-0001-codex-source-of-truth.md) — Le Codex comme source de vérité
- [ADR-0002](../ADR/ADR-0002-monorepo-local-first.md) — Monorepo, local-first
- [ADR-0003](../ADR/ADR-0003-governance-kernel.md) — La gouvernance dans le kernel
- [ADR-0004](../ADR/ADR-0004-event-bus.md) — Bus d'événements comme colonne vertébrale
- [RFC-0001](../RFC/RFC-0001-jarvis-kernel-v0.md) — Périmètre du Kernel v0
