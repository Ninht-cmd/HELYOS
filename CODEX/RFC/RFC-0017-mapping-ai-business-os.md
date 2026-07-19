# RFC-0017 — PROMPT MASTER « AI Business OS » : le mapping honnête (assembler, pas réinventer)

- **Statut** : Accepted
- **Date** : 2026-07-18
- **Auteur** : Le Conservateur
- **Entrée** : le « PROMPT MASTER — Architecte d'une usine à cash IA autonome » du fondateur.

## Le verdict d'architecte

Ce prompt décrit une plateforme d'entreprise IA multi-tenant. **À ~80%, c'est HELYOS
à l'échelle v3–v10.** Sa propre règle finale — *« la valeur est dans l'assemblage
intelligent, pas dans la création d'outils »* — nous interdit de déployer 30 conteneurs
ce soir pour gérer 0 client. On mappe, on n'empile pas.

## La table buy-vs-build (comme le prompt l'exige)

| Besoin du prompt | Existe déjà dans HELYOS | Décision |
|---|---|---|
| Boucle VOIR→COMPRENDRE→DÉCIDER→AGIR→MESURER→APPRENDRE | Prompt Fondateur + le Pouls | ✅ acquis |
| Human-in-the-loop N0/N1/N2 | Gouvernance A0–A5 + règles d'or | ✅ acquis (plus fin) |
| « TOUT LOGGER » / Data Fabric | AuditLog + EventBus + MemoryStore | ✅ acquis |
| Guardrails IA avant action externe | PolicyEngine (GR-1/2/3/7) | ✅ acquis, testé |
| AI FinOps / CFO-AI | Livre de caisse + conseiller CFO (RFC-0014, **cette RFC**) | ✅ acquis |
| Agents C-suite (CEO/CFO/CTO…) | **Comité `AdvisoryBoard` — cette RFC** | ✅ **construit** (conseillers A1) |
| Mémoire vectorielle / RAG | NaiveVectorMemory + nomic-embed (Ollama) | 🟡 basique, suffisant |
| LLM local / inférence | Ollama qwen3:14b (RFC-0016) | ✅ acquis |
| Multi-tenant strict, Keycloak, Vault, JWT | — | 🔧 v10 (auth = ADR docs/ACCES.md) |
| Temporal, LangGraph, CrewAI | Orchestrator interne (RFC-0004) | 🟡 suffisant à 1 tenant ; Temporal si reprise-sur-crash requise |
| ERPNext, TwentyCRM, Paperless, Documenso | — | 🔧 connecteurs le jour où un client le paie |
| Traefik, Prometheus, Grafana, Loki, Wazuh | OpenTelemetry (optionnel) | 🔧 quand il y a du trafic à observer |
| docker-compose 30 services | — | ❌ **refusé aujourd'hui** : coût VPS + maintenance pour 0 client |

## Ce qui est construit dans cette RFC : le Comité

Les « AGENTS AUTONOMES » du prompt (CEO, CFO, CTO, COO, CMO, SALES, SUPPORT, RH,
LEGAL, CISO, DATA, RESEARCH) sont livrés — mais en **conseillers gouvernés (A1)**,
pas en exécutants autonomes. Raison de fond : un agent qui dépense/signe/trade seul
viole GR-7/GR-2. Chaque C-level analyse la situation **réelle** (caisse, portefeuille,
prospection injectés dans son prompt via qwen3:14b) sous son angle, et **recommande**.

- Chat : « demande au CFO… », « que conseille le CMO », « avis du comité ».
- API : `GET /advisory/roles`, `POST /advisory`.
- Vérifié live : CFO ancré dans la trésorerie réelle ; CMO recommande vitrine+YouTube
  (cohérent RFC-0015) ; un conseiller n'émet qu'une action ANALYZE, jamais FINANCIAL.

## La ligne rouge, réaffirmée

Le prompt veut des agents qui « exécutent » pendant que l'humain dort. HELYOS refuse
pour l'argent, les contrats, les suppressions : ce n'est pas une limite technique,
c'est la règle d'or. Douze experts qui conseillent > douze robots lâchés sur un compte
en banque. La sophistication sert la mission ; elle ne met jamais le patrimoine en jeu.

## Déclencheur de la suite (comme toujours)

Chaque brique 🔧 (multi-tenant, ERP/CRM, observabilité, orchestration lourde) devient
réelle quand un revenu la finance — pas avant. C'est la doctrine (RFC-0008/0015), et
c'est aussi, mot pour mot, la règle « ne pas réinventer » du prompt lui-même.
