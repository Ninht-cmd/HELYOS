# RFC-0011 — Pilotage v2 (le beau + le vrai) & accès iPhone (PWA)

- **Statut** : Accepted
- **Date** : 2026-07-09
- **Auteur** : Le Conservateur
- **Principes ADN engagés** : 8 (honnêteté), 14 (local d'abord)

## 1. Le problème (posé par le fondateur, captures à l'appui)

Deux artefacts existaient : une maquette **belle mais mensongère** (CA 124 500 € inventé,
entreprises fantômes) et un pilotage **honnête mais austère**, dont le fallback LLM
produisait du vide verbeux (« ### 1. Compréhension du sujet » sur une question ambiguë).

Doctrine retenue : **le beau vient du design, jamais de faux chiffres.**

## 2. Pilotage v2 (`web/board.html`)

Repris de la maquette : actions rapides en tuiles colorées, avatars colorés par type de
business, vue d'ensemble, hiérarchie visuelle, hover states. Refusé de la maquette :
tout chiffre inventé, toute entreprise fantôme, tout faux message. Les sources restent
inchangées : `/portfolio/detail`, `/governance/audit`, `/events`, `/connectors`.
Les entreprises rêvées de la maquette sont remplacées par UNE carte « + Nouvelle
entreprise » : l'ambition affichée comme un emplacement vide, pas comme un mensonge.

## 3. Fallback LLM corrigé (le bug du « vide verbeux »)

- `agents/research.py` : le prompt d'analyse est désormais contraint (persona +
  prose simple, 120 mots max, pas de titres ; si la demande est ambiguë → UNE question
  de clarification au lieu d'une pseudo-analyse de la formulation).
- `jarvis.py` : le classifieur LLM reçoit la règle « question de suivi / question sur
  HELYOS / message trop vague = conversation, pas recherche ».

## 4. Accès iPhone 15 — PWA, pas d'app native

Les deux pages (`index.html`, `board.html`) sont désormais des PWA :
`manifest.webmanifest`, `icon-180.png`/`icon-512.png`, balises `apple-mobile-web-app-*`,
layout responsive (sidebar → barre horizontale collante sous 760 px, safe-areas iOS).

### Procédure (Wi-Fi local, 2 minutes)

1. Sur le PC : lancer le kernel ouvert au réseau local —
   `uvicorn jarvis_kernel.main:app --host 0.0.0.0 --port 8080`
   (autoriser Python dans le pare-feu Windows, réseau **privé** uniquement).
2. Trouver l'IP locale du PC : `ipconfig` → « Adresse IPv4 » (ex. `192.168.1.24`).
3. Sur l'iPhone (même Wi-Fi), Safari → `http://192.168.1.24:8080/app/board.html`.
4. Partager → **« Sur l'écran d'accueil »**. HELYOS devient une icône plein écran.

### Hors du domicile : Tailscale, jamais d'ouverture de box

Pour accéder à HELYOS depuis n'importe où : installer Tailscale (gratuit, WireGuard)
sur le PC et l'iPhone, même compte → le PC obtient une IP stable `100.x.y.z`, joignable
uniquement par tes appareils. **Ne jamais ouvrir le port sur la box / ne jamais exposer
le kernel à Internet** : l'API n'a pas d'authentification (elle est conçue locale
d'abord) ; l'exposer publiquement = n'importe qui parle à Jarvis. Une couche d'auth
(token) sera une RFC dédiée si un jour l'usage le demande.

### Limites dites honnêtement

- Le PC doit être allumé et le kernel lancé : HELYOS est local d'abord, il n'y a pas de cloud.
- Pas de notifications push (nécessiterait HTTPS + service worker + APNs : hors périmètre).
- La 3D du chat est allégée par le navigateur iOS selon la batterie — c'est normal.

## 5. Ce que cette RFC ne fait PAS

- Pas d'app iOS native, pas de compte cloud, pas de télémétrie.
- Pas d'authentification API (locale/tailnet uniquement — voir avertissement ci-dessus).
- Le gel du noyau (RFC-0008) reste en vigueur : ceci est de l'UI et un correctif de bug,
  aucune capacité nouvelle n'a été ajoutée au noyau.
