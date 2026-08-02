# HELYOS — Architecture Specification v1.0

- **Statut** : Consolidé · **Date** : 2026-08-02 · **Portée** : `apps/jarvis-kernel` (le noyau) + interfaces
- **Consolide** : RFC-0001→0019, ADR-0001→0012, DD-0001, CODEX/02_ARCHITECTURE, CODEX/07_TECH.
- **Autorité** : ce document décrit ce qui **existe dans le code** (vérité-terrain), et distingue
  explicitement l'implémenté du prévu. En cas de conflit avec une RFC antérieure, cette spec fait foi ;
  au-dessus d'elle, seul le Codex (vision/gouvernance) prime.

---

## 1. Résumé exécutif

**Ce qu'est HELYOS.** Un noyau logiciel *local-first* qui transforme un objectif d'entreprise en
décisions gouvernées. Formellement, un **contrôleur décisionnel séquentiel sous incertitude** (cadre
POMDP, cf. DD-0001) : il maintient un **modèle d'état probabiliste** de l'entreprise, évalue une
**fonction d'utilité explicite**, et propose la **meilleure action** — le tout borné par une
**gouvernance à six niveaux (A0–A5)** qui garantit qu'aucune action sensible (argent, envoi, suppression)
ne s'exécute sans validation humaine.

**État de maturité (honnête).** HELYOS est aujourd'hui un **contrôleur glouton à horizon 1** sur une
croyance factorisée gaussienne mise à jour par fusion de mesures, avec une récompense heuristique
explicite et une gouvernance mûre. Il **n'est pas** un solveur de POMDP, ne fait pas de planification
multi-pas ni d'apprentissage en ligne (cf. §10, §11).

**Architecture en une phrase.** Un **cœur en Python pur (stdlib)** — gouvernance, modèle du monde,
mémoire, bus d'événements, agents — exposé par une **couche API optionnelle** (FastAPI) et un **serveur
MCP**, câblé par un unique *composition root* (`KernelContext`), persisté en SQLite, et branché au monde
par des **connecteurs gouvernés** et un **client MCP**.

**Propriétés clés.**
1. *Local-first* : le cœur tourne sans aucun service externe ; LLM (Ollama), vecteurs (Qdrant),
   mémoire (Postgres) et tracing (OTel) sont tous **optionnels** avec repli intégré.
2. *Governance-first* : toute action passe par `GovernanceService.submit()`. Les règles d'or
   (jamais d'argent/d'envoi/de suppression autonome) sont un **invariant**, pas une option.
3. *LLM comme estimateur, pas comme système* : le LLM propose (intentions, croyances, texte, code) ;
   l'arbitrage des décisions est numérique (utilité), et l'exécution est gouvernée.
4. *Codex source de vérité* : les décisions d'architecture vivent dans `CODEX/` (ADR/RFC/DD) ; le code
   les implémente.

**Interfaces d'entrée.** (a) HTTP/JSON (≈ 45 endpoints, dont le cockpit web servi sous `/app`),
(b) serveur **MCP** (stdio JSON-RPC) pour brancher un client type Claude, (c) **CLI** conversationnelle.

**Ce qui reste à construire** (chemin critique, §12) : transition stochastique + étape de prédiction →
planification en espace de croyance (QMDP/POMCP) → apprentissage en ligne du modèle de transition. C'est
le passage du *contrôleur à un pas* à l'*agent adaptatif multi-horizon*.

---

## 2. Principes & cadre théorique

- **Problème résolu** : décision séquentielle sous observabilité partielle — `π* = argmax_π E[Σ γᵗ R(xₜ,aₜ)]`
  sur la croyance `bₜ = P(xₜ | o₁:ₜ)`. Détail et positionnement honnête : **DD-0001**.
- **Invariants** :
  1. *Local-first / stdlib-core* — le paquet `jarvis_kernel` n'importe hors-stdlib que `fastapi/pydantic`
     (couche API) et `sqlite3/smtplib/email/csv/unicodedata` (stdlib). Tout le reste est optionnel.
  2. *Governance-first* — aucune capacité n'agit hors de `GovernanceService`.
  3. *Réversibilité par défaut* — GR-1 : pas de suppression sans sauvegarde.
  4. *Honnêteté* — jamais de chiffre inventé ; l'incertitude est représentée (σ) et affichée.

---

## 3. Vue d'ensemble en couches

```
┌─────────────────────────────────────────────────────────────────────┐
│ INTERFACES     HTTP/JSON API (FastAPI)  ·  Serveur MCP  ·  CLI  ·  Web/app │
├─────────────────────────────────────────────────────────────────────┤
│ CONVERSATION   Jarvis (routage d'intention → handler)  ·  chat.py          │
├─────────────────────────────────────────────────────────────────────┤
│ DÉCISION       world/ (état S_t → utilité U → politique π)                 │
│                reasoning/ (cerveau ReAct, estimateur+exécuteur d'outils)   │
│                advisory/ (comité C-suite, couche explicative)              │
├─────────────────────────────────────────────────────────────────────┤
│ DOMAINE        business/ (portfolio, ledger, orders, prospection)          │
│                agents/ (market, paper_trader, invoice_reminder, scribe, …) │
├─────────────────────────────────────────────────────────────────────┤
│ CAPACITÉS      integrations/ (web, codegen, engineering, mcp_client, …)    │
│                connectors/ (github, market, ollama, shopify, smtp, trading)│
├─────────────────────────────────────────────────────────────────────┤
│ GOUVERNANCE    GovernanceService = PolicyEngine + gates + AuditLog         │
├─────────────────────────────────────────────────────────────────────┤
│ PLATEFORME     KernelContext · EventBus · Memory(+Vector) · Pulse ·        │
│                observability · licensing · config                         │
└─────────────────────────────────────────────────────────────────────┘
        Composition root unique : context.build_default_context()
```

---

## 4. Catalogue des composants

Notation maturité : `L0` concept · `L1` prototype · `L2` fonctionnel · `L3` validé scénarios ·
`L4` validé données réelles · `L5` boucle fermée prod (cf. DD-0001).

### 4.1 Gouvernance — `governance/`

| Composant | Fichier | Rôle | Interface clé | Algorithme | Mat. |
|---|---|---|---|---|---|
| `AutonomyLevel` | autonomy.py | Échelle A0–A5 (IntEnum) | `from_name()`, `.label` | ordre total ; défaut sûr A1 | L4 |
| `ActionType`,`Decision`,`Action`,`PolicyVerdict` | policy.py | Vocabulaire d'action + verdict | dataclasses | — | L4 |
| `PolicyEngine` | policy.py | Décide `ALLOW/REQUIRE_VALIDATION/DENY` | `evaluate(action, granted)` | `REQUIRED_LEVEL[type]` + gates | L4 |
| `ReclassifierGate` | reclassifier.py | Requalifie une action mal typée (lexique normalisé) | `reclassify(action)` | normalisation + lexique | L3 |
| `EmbeddingReclassifier` | embedding_reclassifier.py | Requalif. sémantique | `classify()` | cosinus vs prototypes (Ollama) | L2* |
| `FlagVerifier` | flag_verifier.py | Détecte fuite/canary sur action | `check(action)` | clé d'action + secret | L3 |
| `AuditLog`,`AuditEntry` | audit.py | Journal append-only des verdicts | `record()`, `entries()` | horodatage immuable | L4 |
| `GovernanceService` | service.py | Façade : soumet une action, applique gates, journalise, émet | `submit(action, granted) → PolicyVerdict` | orchestration | L4 |

`*` Les gates `ReclassifierGate` / `EmbeddingReclassifier` / `FlagVerifier` sont **validés en banc
adversarial** (`eval/governance_bench.py`) mais **non câblés dans le `submit()` live** (cf. §11.6) ;
l'étage embedding exige Ollama (repli lexique sinon).

### 4.2 Décision — `world/`, `agents/reasoning.py`, `agents/advisory.py`

| Composant | Fichier | Rôle | Interface clé | Algorithme | Mat. |
|---|---|---|---|---|---|
| `Belief`,`WorldModel` | world/model.py | État probabiliste S_t (graphe de croyances) | `observe()`,`derive()`,`snapshot()`,`save/load()` | **fusion bayésienne gaussienne** ; **propagation d'incertitude** (jacobienne num.) ; décroissance de confiance | rep. L3 / filtre L2 |
| `utility` | world/decision.py | Fonction d'utilité U(S) | `utility(world, now) → (score, décomposition)` | scalarisation pondérée-confiance | L3 |
| `Action`,`Policy`,`Decision` | world/decision.py | Politique π | `decide(world, actions, now)` | **argmax glouton ΔU, horizon 1** | L3 |
| `seed_world`,`default_actions` | world/seed.py | Amorçage S_t depuis l'état réel | `seed_world(ctx, now)` | mapping caisse/prospection/risques | L3 |
| `ReasoningAgent` | agents/reasoning.py | Cerveau ReAct : objectif → outils → synthèse | `run(goal, granted, max_steps)` | boucle ReAct ; `_json_objects()` (scanner d'accolades) ; cache anti-répétition ; ~24 outils gouvernés | L3 |
| `AdvisoryBoard`,`Role` | agents/advisory.py | Comité C-suite (12 rôles) — **couche explicative** | `advise(ctx, gov, msg, granted)` | sélection de rôle + ancrage sur l'état | L3 |

> **Autorité décisionnelle (réconciliation, cf. §11.1).** `world/` est la **colonne vertébrale
> décisionnelle** (état → utilité → argmax). `reasoning/` est l'**estimateur/exécuteur** : il enchaîne
> des outils gouvernés pour atteindre un objectif et peut alimenter le World Model. `advisory/`
> **explique** (verbalise une recommandation) et n'a **aucune autorité d'exécution**.

### 4.3 Domaine business — `business/`

| Composant | Fichier | Rôle | Interface clé | Algorithme | Mat. |
|---|---|---|---|---|---|
| `Business`,`BusinessPortfolio` | portfolio.py | Portefeuille de business + tâches | `list()`,`summary()`,`add()`,`complete_task()` ; `seed_known_businesses()` | agrégation d'état | L4 |
| `Entry`,`Ledger` | ledger.py | Livre de caisse append-only par business (RFC-0014) | `add()`,`global_summary()` | CA = Σ recettes ; solde = Σ | L4 |
| `Order`,`OrderBook` | orders.py | Ventes/achats, à livrer/encaisser, fournisseurs | `add()`,`summary()`,`set_status()` | agrégation | L3 |
| `Prospect`,`ProspectionPipeline` | prospection.py | Pipeline prospects + relances | `stats()`,`add()`,`set_status()`,`due()` | étapes + relances J+3/J+7 | L3 |

### 4.4 Agents de domaine — `agents/`

| Composant | Rôle | Interface | Algorithme | Mat. |
|---|---|---|---|---|
| `MarketAnalystAgent` | Lecture marché (crypto) | `analyze(gov, symbols)` | SMA, RSI(14), tendance | L3 |
| `PaperTrader` | Simulation trading (argent fictif, RFC-0013) | `summary()`,`step()` | portefeuille virtuel | L2 |
| `InvoiceReminderAgent` | Relances factures graduées (RFC-0006) | `plan()` | ton selon jours de retard | L3 |
| `BusinessScaffolder` | Génère un squelette de business (RFC-0005) | `scaffold(gov, …, granted)` | plan produit → tâches | L2 |
| `ScribeAgent` | Rédige ADR/RFC (Codex) | `render_adr()`, `run()` | gabarit + slug | L3 |
| `ResearchAgent` | Recherche/synthèse | `run(msg, granted)` | LLM + web | L2 |
| `Nvidia/OpenSourceLabAgent` | Wrappers gouvernés des labs | `run(granted)` | délègue aux intégrations | L2 |
| `Orchestrator` | Enchaînement de steps (RFC-0004) | `run(steps)` | séquence + résultats | L2 |
| `AgentRegistry`,`Agent`,`ObserverAgent` | base.py | Socle + registre | `required_level`, dispatch | L4 |

### 4.5 Capacités — `integrations/`

| Composant | Rôle | Interface | Algorithme / notes | Mat. |
|---|---|---|---|---|
| `web` | Recherche + lecture web (SSRF-safe) | `web_search()`,`web_fetch()` | DuckDuckGo IA + Wikipédia ; garde IP privées | L2 |
| `codegen` | Génère code (vérifié) + plans | `generate_code()`,`engineering_plan()`,`business_plan()` | LLM → fichier → **py_compile** ; plans Markdown structurés | L2 |
| `engineering` | Pièces 3D + méca (Python pur) | `generate_part()`,`mechanical()` | STL ASCII (triangles/engrenage) ; ratio, flèche poutre, couple de serrage | L2 |
| `mcp_client`,`MCPServerSpec` | Client MCP (se branche à tout) | `list_tools()`,`call_tool()` | JSON-RPC stdio ; `load_specs()` | L2 |
| `ModuleRegistry`,`Module` | Interrupteurs on/off des modules | `list()`,`toggle()` | persistance + sonde | L3 |
| `OpenSourceLibrary` | Recherche catalogue open-source local | `search()` | TSV local | L2 |
| `NvidiaLab`,`OpenSourceLab` | Inventaire GPU / dépôts | `status()`,`assets()`,`sync()` | sondes locales | L2 |

### 4.6 Connecteurs gouvernés — `connectors/` (RFC-0009)

`Connector`/`EnvConnector` (base) + `ConnectorStatus`. Implémentations : **GitHub**, **MarketData**,
**Ollama**, **Shopify**, **SMTP**, **TradingView**. `build_connectors(settings)` (registre),
`statuses()`. Interface : `status() → ConnectorStatus`, `sync(portfolio)` (optionnel). État réel :
GitHub/Ollama/Market fonctionnels ; Shopify/SMTP/Trading = coquilles tant que les identifiants ne sont
pas fournis (statut `à connecter`, honnête).

### 4.7 Plateforme

| Composant | Fichier | Rôle | Interface |
|---|---|---|---|
| `KernelContext` | context.py | **Composition root** unique | `build_default_context()` |
| `EventBus`,`Event` | kernel/event_bus.py | Bus pub/sub interne (ADR-0004) | `emit()`,`subscribe(pattern)` |
| `MemoryStore` (In-Memory / SQLite / Postgres) | memory/ | Persistance clé/valeur namespacée | `remember()`,`recall()` ; `build_memory(backend)` |
| `VectorMemory` (Naive / Qdrant) | memory/vector.py | Recherche sémantique | `add()`,`search()` ; cosinus TF (Naive) |
| `Pulse`,`PulseItem` | pulse.py | Observation continue + briefing (RFC-0012) | `start()`,`stop()`,`report()` ; watchers |
| observability | observability/ | Logs JSON + tracing OTel optionnel | `get_logger()`,`span()` |
| licensing | licensing/license.py | Entitlements signés (ADR-0005) | `sign_license()`,`verify_license()` ; HMAC |
| `Settings` | config.py | Configuration par variables d'env | `default_settings` |

### 4.8 Interfaces externes

- **HTTP/JSON API** (`api/routes.py`, `main.py`) — voir §6. Sert aussi le cockpit web sous `/app`.
- **Serveur MCP** (`mcp_server.py`) — `handle_request()`, `call_tool()` : expose les capacités
  d'HELYOS à un client MCP (ex. Claude) en JSON-RPC stdio.
- **CLI** (`chat.py`) — boucle conversationnelle locale.
- **Web UI** (`web/`) — `cockpit.html` (console autonome), `board.html` (tableau de bord), `index.html`
  (mode immersif/voix).

---

## 5. Interfaces (contrats stables)

```
LLMPort.complete(prompt: str, **kwargs) -> str                     # agents/llm.py
MemoryStore.remember(key, value, namespace) / recall(key, namespace)
VectorMemory.add(id, text, meta) / search(query, k) -> [VectorHit]
Connector.status() -> ConnectorStatus ; Connector.sync(portfolio) -> str|None
Agent.required_level: AutonomyLevel ; (handlers spécialisés par agent)
GovernanceService.submit(action: Action, granted: AutonomyLevel) -> PolicyVerdict
EventBus.emit(name, **data) ; EventBus.subscribe(pattern, handler)
Jarvis.classify(message) -> intent ; Jarvis.handle(message, granted) -> JarvisReply
WorldModel.observe/derive/snapshot/save/load ; Policy.decide(world, actions, now) -> [Decision]
```

Ports abstraits (points d'extension) : `LLMPort` (Stub/Ollama/LiteLLM), `MemoryStore`
(InMemory/SQLite/Postgres), `VectorMemory` (Naive/Qdrant), `EmbedderPort` (Ollama), `Connector`.

---

## 6. Interface HTTP (catalogue des endpoints)

| Domaine | Endpoints |
|---|---|
| Santé/état | `GET /health`, `GET /cockpit/topology`, `GET /info`, `GET /classic` |
| Gouvernance | `GET /governance/levels`, `GET /governance/audit`, `POST /intent`, `GET /events` |
| Conversation | `POST /jarvis`, `GET /jarvis/history` |
| Business | `GET /portfolio`, `GET /portfolio/detail`, `POST …/complete_task`, `GET/POST /ledger`, `GET/POST /orders`, `GET/POST /prospection` |
| Décision/cerveau | `POST /agent/run` |
| Conseil | `GET /advisory/roles`, `POST /advisory/ask` |
| Capacités | `POST /engineering/part`, `POST /engineering/calc`, `GET /modules` + `POST /modules/toggle`, `GET /library/search` |
| MCP | `GET /mcp/servers`, `POST /mcp/tools`, `POST /mcp/call` |
| Marché/simu | `GET /paper` + `POST /paper/step` |
| Labs | `GET /nvidia/*` + `POST /nvidia/sync`, `GET /open-source/*` + sync |
| Connecteurs | `GET /connectors`, `POST /connectors/sync` |
| Pouls | `GET /pulse/briefing` |
| Agents | `GET /agents` |

Schémas Pydantic : `api/schemas.py` (Health, Verdict, Portfolio, Briefing, JarvisReply, …).

---

## 7. Modèle de données & persistance

- **Persistance** : `MemoryStore` clé/valeur **namespacée** (SQLite par défaut : `HELYOS_MEMORY_BACKEND=sqlite`,
  `HELYOS_MEMORY_PATH`). Namespaces : `conversation` (thread), `world` (état S_t), `factures`,
  `prospection`, `orders`, `ledger:<business>`, `modules`, etc.
- **Livres append-only** : `Ledger` (écritures), `AuditLog` (verdicts) — jamais de mutation en place.
- **Vecteurs** : `VectorMemory` (Naive TF-cosinus local ; Qdrant optionnel).
- **Artefacts générés** (gitignorés) : `generated/code`, `generated/plans`, `pieces_3d/`.

---

## 8. Modèle de gouvernance (normatif)

**Niveaux** A0 Lecture · A1 Préparation · A2 Exécution validée · A3 Faible risque · A4 Gestion contrôlée ·
A5 Stratégique.

**Plancher par type d'action** (`REQUIRED_LEVEL`) :

| ActionType | Niveau requis | Note |
|---|---|---|
| READ | A0 | observer |
| ANALYZE | A1 | proposer/simuler |
| WRITE_LOCAL | A2 | écrire un fichier |
| DELETE | A2 | + GR-1 (sauvegarde préalable) |
| EXTERNAL_SENSITIVE | A2 | e-mail/publication/appel tiers |
| FINANCIAL | A2 | transaction |
| RENAME_WORKDIR | A3 | réversible |
| SELF_PERMISSION | A5 | de toute façon interdit (GR-3) |

**Règles d'or (invariants, priment sur le niveau)** : GR-1 pas de suppression sans sauvegarde · GR-2 toute
action externe exige validation · GR-3 pas d'auto-élévation de permissions · GR-7 finance jamais autonome.

**Invariant de sûreté (vérifié dans le code)** : `PolicyEngine.evaluate()` évalue les **règles d'or
AVANT** le plancher de niveau. Donc `FINANCIAL` (GR-7) et `EXTERNAL_SENSITIVE`/`sensitive` (GR-2) sans
`validated=True` renvoient **toujours** `REQUIRE_VALIDATION`, quel que soit le niveau accordé (même A5) ;
`SELF_PERMISSION` → `DENY` (GR-3) ; `DELETE` sans `has_backup` → `DENY` (GR-1). Le plancher A2 n'est donc
jamais l'unique rempart pour ces actions.

**Chaîne d'évaluation (chemin live)** : `submit()` → `PolicyEngine.evaluate()` — (1) DENY absolu des
règles d'or non rattrapables (GR-3, GR-1) ; (2) `REQUIRE_VALIDATION` forcée (GR-7, GR-2) ; (3) test de
niveau `granted ≥ required` — → `AuditLog.append()` → `EventBus.emit(governance.decided` + `action.{allowed
|pending_validation|denied})`. Les gates de durcissement (`ReclassifierGate`, `EmbeddingReclassifier`,
`FlagVerifier`) **ne sont pas dans ce chemin** (cf. §11.6).

---

## 9. Dépendances

**Externes** — cœur : **aucune hors-stdlib**. Couche API : `fastapi`, `uvicorn`, `pydantic` (optionnel
`[api]`). Optionnels à l'exécution : **Ollama** (LLM + embeddings), **Qdrant** (vecteurs), **Postgres**
(mémoire), **OpenTelemetry** (tracing) — chacun avec repli local.

**Internes (sens des dépendances, du haut vers le bas)** : Interfaces → Conversation → Décision → Domaine
→ Capacités/Connecteurs → Gouvernance → Plateforme. Le `KernelContext` est le seul point qui assemble le
tout ; aucun module de plateforme ne dépend d'une couche supérieure (règle de dépendance respectée).

---

## 10. Maturité (synthèse DD-0001)

| Capacité | Mat. | Capacité | Mat. |
|---|---|---|---|
| Représentation de croyance | L3 | Simulation / transition | L1 |
| Fusion de mesures | L2 | Planification multi-horizon | L0 |
| Fonction d'utilité | L3 | Découverte d'opportunités | L0 |
| Politique gloutonne (H=1) | L3 | Optimisation de portefeuille | L0 |
| Gouvernance A0–A5 | L4 | Apprentissage en ligne | L0 |
| API / persistance / MCP | L3–L4 | Interfaces (API/MCP/CLI/Web) | L3 |

---

## 11. Incohérences & doublons — résolus

**11.1 Triple autorité décisionnelle** (`reasoning` vs `advisory` vs `world`). *Résolu* : `world/` décide
(numérique), `reasoning/` estime & exécute des outils, `advisory/` explique. Une seule source d'autorité
d'ordre : `Policy.decide()`.

**11.2 Identité HELYOS / STARK / JARVIS.** Plusieurs docs (RFC-0003 arbitrage du nom, ADR-0006 fusion des
stacks, ADR-0011). *Résolu* : **ADR-0011 fait foi** — HELYOS = cerveau gouverné, STARK = corps/cockpit
desktop (:4242), JARVIS = pont cognitif. RFC-0003/ADR-0006 sont historiques sur ce point.

**11.3 Financier au plancher A2 vs « jamais autonome » (GR-7).** *Incohérence apparente — levée.*
Vérification du code (`policy.py`) : les règles d'or court-circuitent **avant** le test de niveau.
`FINANCIAL`/`EXTERNAL_SENSITIVE` non validés → `REQUIRE_VALIDATION` même à A5 ; `SELF_PERMISSION` → `DENY` ;
`DELETE` sans sauvegarde → `DENY`. Le plancher A2 = « exécutable après accord humain », pas « seul ».
**Pas de trou.**

**11.4 Doublons agent ↔ intégration** (`nvidia_lab`, `open_source_lab` dans `agents/` **et**
`integrations/`). *Résolu* : convention de couches — `integrations/*` = bibliothèque de capacité (sans
gouvernance), `agents/*` = enveloppe **gouvernée** exposée à Jarvis. Pas de duplication de logique.

**11.5 Connecteurs vs intégrations vs modules.** *Résolu* : `connectors/` = ponts **gouvernés** vers des
services externes (statut/sync) ; `integrations/` = capacités internes ; `integrations/modules.py` =
interrupteurs on/off (anti-saturation). Frontières désormais explicites.

**11.6 Gates de durcissement non câblés en production.** *Finding réel (à traiter).* `ReclassifierGate`
(requalification par le contenu), `EmbeddingReclassifier` (sémantique) et `FlagVerifier` (preuve crypto)
existent et **passent le banc adversarial** (`eval/governance_bench.py` applique `engine.evaluate(
gate.reclassify(action), …)`), mais ne sont **pas invoqués** dans le `submit()` live ni dans
`KernelContext`. Conséquence : une action au **type sous-déclaré** (« supprime » étiquetée `READ`) n'est
requalifiée qu'en banc, pas en production. **Action : câbler `ReclassifierGate` dans
`GovernanceService.submit()` (avant `evaluate`), l'étage embedding en option.**

**11.7 Roadmaps multiples** (CODEX/06_ROADMAP, roadmaps de RFC, DD-0001). *Résolu* : §12 est la roadmap
consolidée unique ; les autres deviennent des sources historiques.

---

## 12. Roadmap de développement consolidée

**Jalon actuel (v1.0)** : contrôleur glouton H=1 + gouvernance mûre + interfaces (API/MCP/CLI/Web).

**Chemin critique — devenir adaptatif multi-horizon** (détail DD-0001 §7) :
- **A. Transition stochastique `T(b'|b,a)` + étape de prédiction.** Débloque le lookahead. *(simulation
  L1→L2 ; fusion→filtre L2→L3)*
- **B. Planification en espace de croyance.** QMDP puis POMCP/MCTS ; `V = Σ γᵗ U(bₜ)`. *(planification
  L0→L2)*
- **C. Apprentissage en ligne de `T` + calibration de `U`.** Observer le Δ réel post-action, mettre à jour
  le modèle (régression bayésienne). Ferme Feedback→Learning. *(apprentissage L0→L2 ; utilité L3→L4)*
- **D. Valeur de l'information / perception active.** Sans revendiquer l'Active Inference.
- **E. Croyance plus riche.** Covariances croisées + facteurs non gaussiens (Beta, Poisson). *(rep. L3→L4)*

**Parcours produit (parallèle, non bloquant sur A–E)** : fermer la boucle d'encaissement (compte de
paiement + immatriculation), brancher les connecteurs money (Shopify/SMTP), premier client — c'est ce que
la politique π classe déjà en tête (ΔU) sur l'état réel.

**Durcissements transverses** : **câbler `ReclassifierGate` dans `submit()`** (cf. §11.6) + test de
non-régression ; voix locale (RFC-0016) ; recherche web plus profonde (clé Brave/Tavily).

---

## 13. Annexe — index des sources consolidées

- **Fondations** : ADR-0001 (Codex source de vérité), ADR-0002 (monorepo local-first), ADR-0003
  (noyau de gouvernance), ADR-0004 (bus d'événements), ADR-0007 (mémoire/observabilité/scribe).
- **Identité & stacks** : ADR-0006, ADR-0011 (**canonique**), RFC-0003 (historique).
- **Économie & légal** : ADR-0005 (licence), ADR-0008 (open-core), ADR-0009 (conformité), ADR-0010
  (stack self-hosted), ADR-0012 (client MCP).
- **Fonctionnel** : RFC-0001 (kernel v0), 0002 (scribe), 0004 (orchestration), 0005 (scaffolder),
  0006 (relance factures), 0007 (couche conversationnelle), 0008 (plan cash 90 j), 0009 (connecteurs),
  0010 (marché+MCP), 0011 (accès iPhone), 0012 (le vrai Jarvis / Pouls), 0013 (simulation trading),
  0014 (dossier business/ledger), 0015 (produits), 0016 (voix locale RTX), 0017 (mapping AI Business OS),
  0018 (cerveau ReAct), 0019 (World Model + utilité + décision).
- **Théorie** : DD-0001 (contrôle séquentiel sous incertitude).

*Fin — HELYOS Architecture Specification v1.0.*
