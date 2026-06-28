# C4 — Niveau 3 : Composants du Kernel Jarvis

`v0.2` · Statut : **Implémenté (v0)** → [`apps/jarvis-kernel`](../../apps/jarvis-kernel/README.md)

---

L'intérieur du conteneur **Jarvis Kernel**. Ces composants existent **réellement en code** dans la v0.2.

```
┌──────────────────────── JARVIS KERNEL ────────────────────────┐
│                                                               │
│   ┌─────────────┐      API (FastAPI)      ┌────────────────┐  │
│   │   api/      │  /health /agents /intent│  observability/│  │
│   │  (routes)   │──────────────────┐      │  (telemetry,   │  │
│   └──────┬──────┘                  │      │   audit trace) │  │
│          │ Intent                  │      └───────▲────────┘  │
│          ▼                         │              │ events    │
│   ┌─────────────────┐              │      ┌───────┴────────┐  │
│   │  governance/    │◀─── autorise ┘      │   kernel/      │  │
│   │  AutonomyLevel  │      ou refuse       │  EventBus      │  │
│   │  PolicyEngine   │─────── publie ──────▶│  (pub/sub)     │  │
│   │  AuditLog       │      événements      └───────┬────────┘  │
│   └────────┬────────┘                              │           │
│            │ si autorisé                           │ dispatch  │
│            ▼                                        ▼           │
│   ┌─────────────────┐                     ┌────────────────┐  │
│   │   agents/       │  lit / écrit        │   memory/      │  │
│   │  AgentRegistry  │────────────────────▶│  MemoryStore   │  │
│   │  Agent (base)   │                     │  (mémoire/SQL) │  │
│   └─────────────────┘                     └────────────────┘  │
└───────────────────────────────────────────────────────────────┘
```

## Composants (et leur fichier)

| Composant | Responsabilité | Fichier |
|-----------|----------------|---------|
| **EventBus** | Colonne vertébrale pub/sub. Tout fait *flux d'événements* (ADN 6). | [`kernel/event_bus.py`](../../apps/jarvis-kernel/src/jarvis_kernel/kernel/event_bus.py) |
| **AutonomyLevel** | L'échelle A0–A5. Type sûr, comparable. | [`governance/autonomy.py`](../../apps/jarvis-kernel/src/jarvis_kernel/governance/autonomy.py) |
| **PolicyEngine** | Décide : autoriser / refuser / exiger validation. Applique les règles d'or. | [`governance/policy.py`](../../apps/jarvis-kernel/src/jarvis_kernel/governance/policy.py) |
| **AuditLog** | Trace immuable de toute décision de gouvernance (ADN 16). | [`governance/audit.py`](../../apps/jarvis-kernel/src/jarvis_kernel/governance/audit.py) |
| **MemoryStore** | Interface de mémoire (court/long terme). Impl mémoire par défaut. | [`memory/store.py`](../../apps/jarvis-kernel/src/jarvis_kernel/memory/store.py) |
| **Agent / AgentRegistry** | Contrat d'agent + registre. Chaque agent déclare son niveau requis. | [`agents/base.py`](../../apps/jarvis-kernel/src/jarvis_kernel/agents/base.py) |
| **API** | Surface HTTP (santé, agents, soumission d'intentions). | [`api/`](../../apps/jarvis-kernel/src/jarvis_kernel/api/) |
| **Telemetry** | Logs structurés + hooks OpenTelemetry. | [`observability/telemetry.py`](../../apps/jarvis-kernel/src/jarvis_kernel/observability/telemetry.py) |

## Le flux d'une intention (cœur du système)

```
1. Une Intent arrive (API ou agent)          → "supprimer le fichier X"
2. Le PolicyEngine évalue :
     - niveau d'autonomie courant ?           (ex. A1)
     - niveau requis par l'action ?            (suppression → A2 + règle d'or backup)
     - règles d'or violées ?                   (suppression sans backup → REFUS)
3. Décision : ALLOW · REQUIRE_VALIDATION · DENY
4. AuditLog enregistre la décision (qui, quoi, pourquoi, quand)
5. Si ALLOW → l'EventBus publie ; l'agent agit ; trace de sortie
6. Si REQUIRE_VALIDATION → mise en attente du veto humain
```

Ce flux est la **traduction exécutable de l'ADN** : rien d'important ne se fait sans trace (16), tout est observable (6), l'autonomie ne s'auto-escalade jamais ([règles d'or](../03_GOUVERNANCE/01_Regles_Or.md)).

→ Voir le produit complet : [Jarvis](04_Jarvis.md)
