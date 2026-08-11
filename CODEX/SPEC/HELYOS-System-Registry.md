# HELYOS — SystemRegistry + BrickRegistry (la vérité opérationnelle sondée)

- **Statut** : Accepted · **Date** : 2026-08-11
- **Implémentation** : `integrations/system_registry.py` · `GET /os/registry` · panneau cockpit `web/os.html`
- **Tests** : `test_system_registry.py` (7)

---

## 0. Décision : audit des deux cockpits → une seule source de vérité

Comparaison **factuelle** (lecture seule) :

| | Cockpit Python (`/os.html` + `/os/cockpit`) | `WORKSPACE/HELYOS-WEB-COCKPIT` (Node/TS) |
|---|---|---|
| Backend | **Vivant, in-process avec le Kernel** | Aucun serveur (2 deps : drizzle) |
| Données | **Réelles** (ledger/prospection/pulse/gouvernance) | **JSON figé du 21 juil.** (3,1 Mo) |
| Auth | — | — |
| LLM | Ollama local | **OpenAI cloud** (`.env`) |
| Tool Bus | Oui (même processus) | Non |
| Tests | 428 | 0 |

Montrer un instantané de juillet comme « live » **viole** la règle zéro coquille vide.
**Décision : la source de vérité = le cockpit Python/FastAPI.** Le cockpit Node est conservé en
**RÉFÉRENCE** (idées UX + `dashboard-data.json`), jamais comme état opérationnel → dans le
Registry : `node_cockpit` = catégorie `reference`, jamais `ACTIVE`.

## 1. La règle, faite moteur

Une brique n'est **jamais** `ACTIVE` parce que son code ou sa carte d'UI existe. Elle l'est
seulement si une **sonde réelle** le prouve. Garde-fou dur dans `BrickStatus.__post_init__` :
`ACTIVE` sans (`engine` | `api` | `real_data`) est automatiquement déclassé. Sept états :
`ACTIVE · AVAILABLE · DEGRADED · MISCONFIGURED · BROKEN · STOPPED · MISSING`.

Sondes (lecture seule, aucune installation/démarrage) : HTTP (`:11434` Ollama), ports
(`:6333` Qdrant, `:5432` PG), `nvidia-smi`, `docker version`, présence de source clonée,
état interne du Kernel. `DISCOVER → VERIFY → INTEGRATE → TEST → ACTIVE`.

## 2. Vérité au 2026-08-11 (sondée)

```
OVERALL 48/100   (matériel 100 · ai_runtime 44 · infrastructure 20 · helyos 48 · reference 30)

AI RUNTIME
  ● ollama            ACTIVE     API :11434 ✓ · qwen3:14b/8b, nemotron-4b, nomic-embed
  ● gpu_nvidia        ACTIVE     RTX 5070 Ti 16 Go, pilote 610.62
  ○ embeddings_nomic  AVAILABLE  présent, à brancher sur MemoryStore
  ○ tensorrt_llm/triton/nemo  AVAILABLE  source clonée, NON construite
INFRASTRUCTURE
  ○ docker            STOPPED    CLI installé, daemon arrêté
  ○ qdrant            AVAILABLE  données présentes, service arrêté
  ○ otel              AVAILABLE  hooks présents, désactivés (no-op)
  ✕ postgres          MISSING
HELYOS
  ● gouvernance/mémoire/agents/pulse/engineering/cockpit/api  ACTIVE
  ◐ crm_sales, finance   DEGRADED   backend ✓ mais 0 donnée réelle / connecteur à brancher
  ✕ marketing, sav, rh, administration   MISSING (carte d'UI seulement)
  ✕ iam, manual_override, safe_mode, payment_connector   MISSING
```

Le cockpit `/` lit ce registre : l'UI n'invente plus son état.

## 3. Analyse disque (snapshot, aucune suppression)

`NVIDIA-LAB **89,4 Go**` · `OPEN-SOURCE-LAB **30,1 Go**` · `Ollama 16,4 Go` · `STARK 1,8 Go` ·
HELYOS-WEB-COCKPIT / TRADING-AGENT / repo < 0,2 Go chacun. **Les deux labs ≈ 120 Go pour 116 Go
libres** : pas critique aujourd'hui, mais NVIDIA-LAB (source + miroirs *bare*) est le premier
levier si l'on manque de place. Aucune action automatique — toute optimisation (archiver / NAS /
supprimer) passera en `REQUIRE_VALIDATION`.

## 4. Réutilisation immédiate (rien de neuf téléchargé)

Ollama + `qwen3:14b/8b` + `nemotron-4b` + `nomic-embed-text` + MemoryStore + Docker déjà là +
repos open source déjà présents. Prochain upgrade IA gratuit : brancher `nomic-embed-text` comme
vrais embeddings de la mémoire (fallback conservé). Qdrant reste `AVAILABLE` tant qu'il n'est pas
démarré et validé.

## 5. Suite (ordre validé)

`Manual Override réel → SAFE MODE → IAM natif minimal` (Org/Users/Teams/Roles/Permissions/
Business scopes/AI permissions/AuditLog ; Keycloak en fédération plus tard) → **CRM réel**.
En parallèle, **Front A** : CFG + data-flow interprocédural (prouvera que `CRM→email`,
`Finance→paiement` ne peuvent pas contourner la gouvernance). Le Registry restera la vitre par
laquelle chaque nouvelle brique doit prouver qu'elle est vraiment `ACTIVE`.

Voir [[HELYOS-Enterprise-Cockpit]], [[HELYOS-Critical-Property-AST]].
