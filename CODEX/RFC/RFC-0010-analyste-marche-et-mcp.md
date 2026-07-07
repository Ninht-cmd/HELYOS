# RFC-0010 — Analyste de marché gouverné & serveur MCP (accès Claude)

- **Statut** : Accepted
- **Date** : 2026-07-07
- **Auteur** : Le Conservateur
- **Principes ADN engagés** : 3 (gouvernance), 8 (honnêteté), 14 (local d'abord)

## 1. « Un trading automatisé qui analyse mais me demande mon avis »

C'est exactement la forme que la gouvernance autorise — et la seule :

- **Analyser = libre (A1).** `MarketAnalystAgent` lit des **prix publics réels**
  (connecteur `market`, API publique Binance, aucune clé, lecture seule) et calcule des
  indicateurs classiques : SMA20/SMA50 (tendance), RSI14, variation 24 h.
  C'est de l'observation technique, **pas une prédiction ni un conseil financier** —
  la phrase figure dans chaque réponse.
- **Proposer = gouverné (GR-7).** `propose_trade()` émet une Action FINANCIAL →
  **validation humaine obligatoire, même en A5**. Testé.
- **Exécuter = inexistant, par conception.** Aucun courtier n'est branché. Même une
  proposition **validée** retourne `executed=False` avec la raison. HELYOS prépare,
  le fondateur exécute lui-même chez son courtier. Brancher un courtier un jour sera
  une RFC dédiée avec ses garde-fous (budgets, limites, kill-switch) — pas un patch.
- **TradingView reste interdit** (ADR-0010) : le connecteur `market` lit l'API publique
  Binance, documentée et licite — rien à voir avec contourner des CGU.

Chat : « analyse le marché crypto », « cours du bitcoin » → intention `marche_financier`.
« achète du bitcoin » → action dangereuse → GR-7. Le mot « marché » seul (ex. « marché
des mugs ») reste une étude de marché (recherche), pas de la finance.

## 2. Serveur MCP : Claude a accès à HELYOS

`python -m jarvis_kernel.mcp_server` — MCP sur stdio, JSON-RPC 2.0, stdlib pur.
Outils exposés : `helyos_status`, `helyos_ask` (Jarvis), `helyos_portfolio`,
`helyos_audit`, `helyos_connectors`.

Brancher dans Claude Code : `claude mcp add helyos -- python -m jarvis_kernel.mcp_server`
(avec `PYTHONPATH=apps/jarvis-kernel/src`). Idem Claude Desktop via
`claude_desktop_config.json`.

**Invariant de sécurité (testé)** : le serveur MCP n'ajoute AUCUN pouvoir. Un Claude
qui demande « supprime tout » via MCP se fait refuser (GR-1) comme n'importe quel acteur.
C'est aussi la première brique du « bus d'agents MCP » de la spec noyau V1 (RFC-0008).

## 3. Améliorer le design avec Claude

Trois canaux, du plus direct au plus autonome : (a) cette session Claude Code voit le
repo ET le rendu (outils preview) — c'est déjà le canal principal ; (b) le repo est
public → tout claude.ai avec le connecteur GitHub peut lire le code de l'UI ;
(c) le serveur MCP donne à Claude l'accès au kernel **vivant** (état réel, audit,
portefeuille) pour designer sur des données vraies plutôt que des maquettes inventées.
