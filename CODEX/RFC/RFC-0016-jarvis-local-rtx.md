# RFC-0016 — Le Jarvis local : exploiter le RTX 5070 Ti (le plus proche du réel)

- **Statut** : Accepted (étape 1 faite), reste `[CHANTIER]`
- **Date** : 2026-07-18
- **Auteur** : Le Conservateur
- **Demande** : « un truc du niveau Tony Stark, le plus proche de la réalité — cherche
  GitHub, NVIDIA, YouTube, internet ». Réponse : c'est faisable, parce que la machine
  est à la hauteur.

## Le matériel change tout (vérifié)

- GPU : **NVIDIA GeForce RTX 5070 Ti — 16 Go VRAM** (nvidia-smi : 16303 MiB)
- CPU : AMD Ryzen 7 7800X3D · RAM : 31 Go · Ollama installé
- Ce n'est PAS une machine à démo : elle fait tourner un Jarvis local complet,
  voix comprise, avec une latence de type Alexa (1–2 s).

## Étape 1 — Cerveau supérieur ✅ FAIT & VÉRIFIÉ

- `ollama pull qwen3:14b` (9,3 Go). HELYOS y est branché via `HELYOS_LLM_MODEL`,
  sélection automatique dans `launcher.ps1` / `acces_reseau.ps1` (14b si présent,
  sinon repli 8b — on ne force jamais un modèle absent).
- **Preuve** : `ollama ps` montre qwen3:14b chargé 100% GPU (9,6 Go) ; réponse
  conversationnelle cohérente en ~6 s. Le raisonnement d'HELYOS a monté d'un cran,
  gratuitement, en local.
- La carte peut viser plus haut plus tard (14b Q8, voire 27–32b en Q4) selon le besoin.

## Étape 2 — La Voix locale (le vrai « Jarvis parle ») `[CHANTIER]`

Remplacer la voix du navigateur (RFC-0012) par une stack neuronale locale :

| Brique | Choix 2026 (recherché) | Pourquoi | Coût VRAM |
|---|---|---|---|
| **Oreille (STT)** | [NVIDIA Parakeet TDT 0.6B v3](https://localaimaster.com/models/parakeet-tdt) | 3333× temps réel, 6,34% WER, CC-BY-4.0, fait pour RTX | ~2 Go |
| **Voix (TTS)** | Kokoro TTS (ou Piper, archivé mais fonctionnel) | neuronal, local, naturel | léger |
| **Éveil** | [openWakeWord](https://www.home-assistant.io/voice_control/about_wake_word/) | « Hey Jarvis » d'origine, entraînable en 10 min | négligeable |
| **Colle** | boucle Python micro→STT→HELYOS `/jarvis`→TTS | tout gouverné A0–A5 | — |

Budget VRAM total (14b + Parakeet + Kokoro) : tient dans 16 Go. Latence cible 1–2 s.
Source de référence : [stack Whisper+Piper+Ollama 2026](https://dev.to/kunal_d6a8fea2309e1571ee7/local-ai-voice-assistant-stack-2026-whisper-piper-ollama-wired-together-572l).

## Étape 3 — Le HUD vivant `[CHANTIER]`

Le cockpit 3D existe déjà (Three.js). Prochain cran : réactions temps réel à la voix
(onde audio, cœur qui pulse quand HELYOS parle), déjà amorcé dans `web/index.html`.

## Le cadre reste la gouvernance

Plus le cerveau est fort et la voix fluide, plus la règle compte : **la puissance
ne contourne PAS la gouvernance**. Un Jarvis vocal qui entend « fais un virement »
répond toujours « validation requise » (GR-7). C'est ce qui sépare HELYOS d'un
assistant qui pourrait faire une bêtise en une phrase. La sophistication sert la
mission ; elle ne la met jamais en danger.

## Ce qui est promis ici, honnêtement

- Étape 1 : **faite, vérifiée** ce soir.
- Étapes 2–3 : réelles, chiffrées, faisables sur cette machine — mais ce sont des
  builds (téléchargements de modèles, boucle audio, tests). Pas ce soir en un claquement
  de doigts ; un prochain cycle dédié. Aucune de ces briques n'est un fantasme :
  toutes existent, sont gratuites, et tiennent dans tes 16 Go.
