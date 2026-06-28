# Roadmap HELYOS

`v0.2` · Statut : **Vivant (révisé par RFC)**

---

## Les jalons (du Codex v0.1)

> **Alpha → Beta → V1 → Enterprise → Robotics → Cloud → Edge → AGI Ready.**

Ces jalons ne sont pas un calendrier (ADN 12 : on raisonne en décennies, pas en trimestres) mais une **séquence de capacités**. On ne passe au suivant que lorsque le précédent est **solide, observable et gouverné**.

| Jalon | Capacité atteinte | Porte de sortie (« done » quand…) |
|-------|-------------------|-----------------------------------|
| **Pré-Alpha** *(actuel, v0.2)* | Kernel exécutable : bus, gouvernance A0–A5, mémoire, agents, audit. Codex structuré. | Kernel démarre sans service externe, tests verts, Codex navigable. |
| **Alpha** | Premier agent utile bout-en-bout + mémoire persistante (Postgres/Qdrant) + observabilité (OTel/Langfuse). | 1 friction réelle supprimée et **mesurée** (ADN 14). |
| **Beta** | Plusieurs agents composés (LangGraph), 1–2 modules (ex. Automatisation, Création de contenu). Mode No-AI. | Usage quotidien stable par le Conservateur. |
| **V1** | Jarvis « assistant opérationnel » : Voice + Memory + Business. Dashboard. | Le Conservateur délègue des tâches A3 en confiance. |
| **Enterprise** | Durcissement, multi-utilisateur contrôlé, sécurité (module Cyber), SLA internes. | Premiers revenus Ventures (boucle économique amorcée). |
| **Robotics** | Pont edge/robot, perception (Vision/RuView) → action physique gouvernée. | Une boucle OODA physique gouvernée fonctionne. |
| **Cloud** | Capacités cloud **opt-in** (scalabilité), sans rompre le local-first. | Le cloud augmente sans créer de dépendance. |
| **Edge** | Déploiement distribué edge, faible latence, résilient hors-ligne. | Fonctionne en autonomie sur edge. |
| **AGI Ready** | Architecture prête à intégrer des modèles plus capables **sans refonte**, gouvernance à l'échelle. | L'ajout d'un modèle frontier ne casse aucun principe ADN. |

## Principe de progression

```
   Capacité ──▶ Observable ──▶ Gouvernée ──▶ Mesurée ──▶ Jalon suivant
```

Un jalon n'est jamais « atteint » parce que le code existe : il l'est quand la capacité est **observable**, **gouvernée** (A0–A5 + règles d'or) et **mesurée** (friction supprimée).

## Prochaines actions concrètes (post-v0.2)

1. Brancher une **mémoire persistante** réelle (Postgres + Qdrant) derrière `MemoryStore`.
2. Câbler l'**observabilité** (OpenTelemetry → Langfuse).
3. Écrire le **premier agent utile** (RFC + A2) qui supprime une friction mesurée.
4. Ouvrir **RFC RuView-001** (Labs) et **RFC Cyber-001** (posture défensive).
