# ADR-0010 — Intégration du stack self-hosted (Coolify, Dify, Crawl4AI, Stirling, trading)

- **Statut** : Accepted
- **Date** : 2026-07-02
- **Décideur(s)** : Le Conservateur
- **Principes ADN engagés** : 2, 3, 4, 9, 11
- **Source** : vérification multi-agents groundée (licences + API officielles vérifiées, sources dans le Codex).

## Contexte

Proposition d'intégrer un stack self-hosted à HELYOS : Coolify (déploiement), Dify (prototypage),
Crawl4AI (crawl→RAG), Stirling PDF (PDF/OCR→RAG), un pipeline **trading** (TradingView), et une
stratégie **multi-repo** (8 dépôts). Chaque brique a été vérifiée (réelle ? licence ? API officielle
ou scraping ?).

## Décision

**Principe unique :** le kernel reste l'**arbitre entre intention et exécution**. Chaque brique est
un **side-car** derrière une frontière HTTP/MCP — **jamais vendorée/linkée** dans le code AGPL — et
**rien n'atteint le monde sans passer par le PolicyEngine** (ALLOW / REQUIRE_VALIDATION / DENY + audit).

### Cartographie par niveau de gouvernance

| Niveau | Brique | Rôle | Verdict |
|--------|--------|------|---------|
| **A0 (lecture)** | **Crawl4AI** (Apache-2.0, image + MCP officiels, port 11235) | web → Markdown → chunk → `nomic-embed-text` → Qdrant | ✅ **adopt** |
| **A0 (lecture)** | **Stirling PDF** (open-core, **cœur MIT uniquement**) | PDF/OCR → texte → RAG | 🟡 **adopt (cœur MIT)** |
| **A1 (préparation)** | **Dify** (Modified Apache, **source-available, PAS OSI**) | studio de prototypage de workflows agents, en side-car | 🟡 **prototype only** |
| **A2–A5 (exécution)** | **Coolify** (Apache-2.0, API REST officielle `/api/v1`) | organe d'exécution (deploy/start/stop) **derrière** A0–A5 | ✅ **adopt** |

### Interdits / évités (verdicts durs)

1. **Pipeline trading live via TradingView → AVOID.** Trois raisons cumulées : (a) **impossible**
   par voie officielle (aucune API pour uploader du Pine Script / lancer un backtest / lire le
   Strategy Tester) ; (b) **interdit** par les ToS §3 (automated trading, algorithmic decision-making,
   non-display → ban + « legal measures ») ; (c) **dangereux** (la boucle d'auto-optimisation garantit
   l'**overfitting** ; look-ahead bias du crawler ; dégradation live 30-50%). Les MCP « TradingView »
   existants sont **tous non-officiels** (scraping/automation) → risque de ban.
   → **À la place** : recherche/backtest **strictement expérimental, SANS exécution d'ordres**, avec
   **NautilusTrader** (LGPL, compat AGPL). La **Probability of Backtest Overfitting (PBO)** et le
   **Deflated Sharpe Ratio** deviennent des **règles d'or mesurables** qui **DENY** le passage en live.
   *(Éviter VectorBT = Commons Clause incompatible avec le Pro ; Backtrader = GPL non-AGPL, gelé.)*

2. **Multi-repo (8 dépôts) → AVOID pour un solo.** Modules fortement couplés par la gouvernance →
   refactors atomiques impossibles en multi-repo ; précédent **GitLab** (migration 2→1 dépôt,
   ~150 MR/release de sécu). → **Monorepo PRIVÉ** comme source de vérité + **publication
   unidirectionnelle** (`git subtree split` / splitsh-lite) du **cœur AGPL** vers le repo public.
   **uv workspaces** (un lockfile). Frontière open/privé par **répertoire**, pas par dépôt.

3. **MCP communautaires (write Coolify) → différer.** Le MCP officiel Coolify est READ-ONLY ; pour
   le write, utiliser l'**API REST officielle** directe, pas un MCP tiers non audité.

### Garde-fous non négociables (sinon la gouvernance est court-circuitée)

- **Désactiver l'auto-deploy webhook de Coolify** (git push → deploy) : sinon l'exécution contourne A0–A5.
- **Dify n'exécute jamais directement sur le monde** : seul un appel médié par le kernel atteint l'exécution.
- **Coolify = composant privilégié** (SSH root + secrets) → réseau isolé, MFA, tokens scopés, backups chiffrés, veille CVE.
- Le **credential de l'URL MCP Dify** = un secret (rotation).

## Conséquences

- **Positives** : capacités réelles (RAG, déploiement gouverné, recherche trading) branchées **sans**
  affaiblir la gouvernance ni la propriété AGPL ; toutes les briques retenues sont réelles et bien licenciées.
- **Négatives / coûts** : **coût opérationnel de maintenance** d'une constellation de side-cars
  privilégiés, porté par une seule personne (le vrai piège). Discipline permanente sur la frontière AGPL/Pro.
- **Chemin de sortie** : le kernel tourne **sans aucun** de ces services (local-first) → chaque brique
  est débranchable.

## Séquençage (du plus utile/moins risqué au plus risqué)

1. **Crawl4AI** (A0) → RAG. 2. **Stirling cœur MIT** (A0) → documents. 3. **Coolify** (A2, derrière la
gouvernance) → 1ʳᵉ brique qui *agit*. 4. **Dify** (A1, on-demand). 5. **NautilusTrader** (recherche
gouvernée, **jamais** d'exécution d'ordres).
