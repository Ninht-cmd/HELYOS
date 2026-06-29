# Frontière Open Core — ce qui est ouvert vs. commercial

`v0.3` · Statut : **Adopté** ([ADR-0008](../ADR/ADR-0008-open-core-business-model.md)) · Révisable par RFC

---

> **Règle d'or de la frontière :** une capacité va dans le **cœur ouvert** si elle sert
> l'**adoption, la confiance ou la gouvernance** ; elle va en **Pro/Enterprise** si elle crée
> un **avantage opérationnel spécialisé** pour une organisation. **En cas de doute → cœur**
> (l'ouverture est le défaut, ADN 3). On n'« referme » jamais ce qui a été publié.

## Carte de la frontière

| Domaine | 🟢 Cœur ouvert (AGPL-3.0) | 🔒 Commercial (dépôt privé `helyos-pro`) |
|---------|---------------------------|-------------------------------------------|
| **Kernel** | Bus d'événements, cycle de vie, contexte | — |
| **Gouvernance** | A0–A5, règles d'or, audit, PolicyEngine | Politiques avancées, multi-tenant, conformité sectorielle |
| **API / SDK** | API de base, SDK, contrats d'agents | Connecteurs entreprise certifiés |
| **Mémoire** | `MemoryStore`, SQLite, vectoriel local | **Mémoire distribuée** à l'échelle, RAG managé, rétention/gouvernance données |
| **Agents** | `ObserverAgent`, `ScribeAgent`, `ResearchAgent`, orchestrateur de base | **Agents spécialisés** : juridique, finance, industrie, santé |
| **Orchestration** | Séquences gouvernées (RFC-0004) | **Multi-IA** avancée, graphes complexes, optimisation |
| **Observabilité** | Logs JSON, hooks OTel | Dashboard entreprise, alerting, rapports de conformité |
| **Déploiement** | docker-compose (auto-hébergé) | **Déploiement 1-clic**, SaaS managé, SLA |
| **Support** | Communauté (issues) | Support & MAJ **prioritaires**, dédié |

## Les « joyaux » à protéger en priorité

Par ordre de valeur stratégique (ce qui constitue l'avance d'HELYOS) :

1. **Agents spécialisés métier** — l'expertise encodée (juridique, finance…) = forte valeur, peu réplicable.
2. **Mémoire distribuée & RAG à l'échelle** — la qualité de la mémoire est un différenciateur durable.
3. **Gouvernance avancée / conformité** — le wedge des secteurs régulés.
4. **Données & modèles entraînés** (à terme) — l'actif composé le plus défendable (effet de données).

> Le **cœur de gouvernance reste ouvert** : c'est ce qui crée la confiance et l'adoption.
> Ce sont les **couches spécialisées au-dessus** qui se monétisent.

## Conséquences sur la structure des dépôts

| Dépôt | Visibilité | Licence | Contenu |
|-------|-----------|---------|---------|
| `Ninht-cmd/HELYOS` | **public** | AGPL-3.0 | le cœur ouvert (ce repo) |
| `Ninht-cmd/helyos-pro` ✅ *(créé)* | **privé** | propriétaire | modules Pro/Enterprise — 1ᵉʳ module : `LegalReviewAgent` |
| `helyos-cloud` *(à créer)* | **privé** | propriétaire | infra SaaS, déploiement managé |

> **Preuve de la frontière (v0.1 de `helyos-pro`)** : le `LegalReviewAgent` importe le cœur
> (`jarvis_kernel`) et s'enregistre via `register_pro_agents()` **sans modifier une seule ligne
> du cœur** ; toutes ses actions passent par la gouvernance A0–A5. 6 tests le vérifient.

Le cœur expose des **points d'extension** (ports, registre d'agents, `MemoryStore`, `LLMPort`)
pour que `helyos-pro` se branche **sans modifier** le cœur (modularité, ADN 4). C'est la même
discipline d'interfaces que pour la [fusion](../02_ARCHITECTURE/05_Fusion_HELYOS_Jarvis.md).

## Anti-patterns à éviter

- ❌ Mettre la **gouvernance de base** ou l'**audit** en Pro (ça tuerait la confiance).
- ❌ Dégrader artificiellement le cœur pour pousser au Pro (« crippleware »).
- ❌ Introduire une dépendance du cœur vers un module propriétaire (le cœur doit tourner seul).
- ✅ Le cœur doit rester **pleinement utile seul** ; le Pro **ajoute**, ne **débloque** pas l'essentiel.
