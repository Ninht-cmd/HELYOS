# ADR-0012 — Client MCP : le « Jarvis qui se branche à tout », proprement

- **Statut** : Accepted
- **Date** : 2026-07-24
- **Décideur** : Le Conservateur (« un Jarvis nommé HELYOS qui se branche à tout et fait tout »)

## Contexte

Le fondateur veut un assistant qui « se branche à tout ». En ingénieur, ce n'est
pas un vœu flou : c'est le **client MCP** (Model Context Protocol), le standard
2025-2026 pour connecter un agent à des outils. Des centaines de serveurs MCP
existent (fichiers, Gmail, Slack, Postgres, GitHub…). HELYOS était déjà un
serveur MCP (RFC-0010) — appelable. Il manquait le **client** — pour appeler.

## Décision

Construire un client MCP (`integrations/mcp_client.py`) plutôt que continuer à
coder des connecteurs bespoke. **C'est du levier, pas de la dette** : un protocole
remplace N connecteurs. Ajouter un service = une ligne dans `mcp_servers.json`,
zéro code.

Gouvernance (cohérente avec tout le reste) :
- **Découvrir** les outils d'un serveur = lecture (A1), libre.
- **Appeler** un outil externe = action monde → EXTERNAL_SENSITIVE → GR-2,
  validation humaine. « Fait tout », oui — mais l'irréversible jamais sans toi.
- Rien n'est joignable hors de `mcp_servers.json` ; on ne prétend jamais parler
  à un service qu'on ne peut pas joindre.

## Preuve (mesurée, pas supposée)

Loopback : HELYOS-client → HELYOS-serveur (vrai sous-processus stdio JSON-RPC).
Découverte des 6 outils, appel `helyos_status` → réponse réelle (`agents: 10`).
Un bug de chemin (`parents[4]` au lieu de `[5]` → `apps\apps`) a été trouvé PARCE
QUE le test réel a échoué — d'où la discipline « exécuter, ne pas supposer ».

## Surface

`GET /mcp/servers`, `POST /mcp/tools` (A1), `POST /mcp/call` (GR-2). Transport
stdio, testable sans sous-processus (runner injectable — 4 tests hermétiques).

## Limite honnête

« Se branche à tout » ≠ « est branché à tout ». Chaque serveur MCP vers un vrai
service (Gmail, banque…) exige ses **credentials**, que seul le fondateur crée.
Le protocole est universel ; les clés restent humaines. C'est la même frontière
que partout : HELYOS fournit le tuyau, l'humain fournit l'accès et la validation.
