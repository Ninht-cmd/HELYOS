# HELYOS

> **Helye + OS** — Un système d'exploitation de l'intelligence personnelle.
> *Jarvis est un produit d'HELYOS, pas l'entreprise.*

HELYOS construit une **intelligence opérationnelle gouvernée** : locale d'abord, open-source d'abord, modulaire, auditée, explicable et conçue pour durer plusieurs générations.

---

## 🧭 Par où commencer

1. **Lis le [CODEX](CODEX/README.md)** — c'est la source de vérité. Le Codex prime sur le code.
2. Survole l'**[architecture](CODEX/02_ARCHITECTURE/00_Overview.md)** (modèle C4).
3. Lance le **[kernel Jarvis](apps/jarvis-kernel/README.md)** en local (FastAPI, zéro service externe requis).

```powershell
# Démarrage rapide (Windows / PowerShell)
.\scripts\dev.ps1 setup     # crée le venv + installe le kernel
.\scripts\dev.ps1 test      # lance la suite de tests (stdlib only)
.\scripts\dev.ps1 run       # démarre l'API sur http://127.0.0.1:8080
```

## 🗂️ Structure du dépôt

```
HELYOS/
├─ CODEX/                 # Source de vérité versionnée (vision, ADN, architecture, gouvernance…)
│  ├─ 00_VISION/          # Vision, mission, manifeste
│  ├─ 01_ADN/             # Les principes fondateurs
│  ├─ 02_ARCHITECTURE/    # Modèle C4 (contexte → conteneurs → composants)
│  ├─ 03_GOUVERNANCE/     # Autonomie graduée A0–A5 + règles d'or
│  ├─ 04_MODULES/         # Cybersécurité, Vision, Robotique, RuView, Trading…
│  ├─ 05_ECONOMIE/        # La boucle Recherche → Produits → Revenus → Patrimoine
│  ├─ 06_ROADMAP/         # Alpha → Beta → V1 → … → AGI Ready
│  ├─ 07_TECH/            # Stack technique de référence
│  ├─ ADR/                # Architecture Decision Records
│  └─ RFC/                # Request For Comments (décisions structurantes)
├─ apps/
│  └─ jarvis-kernel/      # Le kernel Jarvis, exécutable (FastAPI)
├─ deploy/                # docker-compose de l'infrastructure locale
├─ scripts/               # Scripts de développement
└─ docs/                  # Documentation générée / annexes
```

## 🧬 Les 3 lois du dépôt

1. **Le Codex est la vérité.** Aucun modèle IA n'est la vérité ; le Codex l'est.
2. **Aucune décision importante ne reste dans une seule conversation.** Elle devient un [ADR](CODEX/ADR/) ou une [RFC](CODEX/RFC/).
3. **Une fonctionnalité doit supprimer une friction mesurable.** Sinon elle n'existe pas.

## 📌 État

| | |
|---|---|
| **Version** | v0.3 (fondations Alpha) |
| **Statut** | Alpha — mémoire persistante, observabilité, premier agent |
| **Écosystème** | Aligné sur Isaac GR00T / Riva / NeMo — voir [état de l'art](CODEX/08_ECOSYSTEME/00_Etat_de_lart.md) & [fusion](CODEX/02_ARCHITECTURE/05_Fusion_HELYOS_Jarvis.md) |
| **Licence** | **AGPL-3.0** (cœur ouvert) + dual-licensing commercial — [ADR-0005](CODEX/ADR/ADR-0005-licence.md) |
| **Modèle** | **Open Core** — [business model](CODEX/05_ECONOMIE/01_Business_Model.md) · [frontière open/Pro](CODEX/05_ECONOMIE/02_Frontiere_Open_Core.md) |
| **Conservateur** | Le fondateur |

Voir le [CHANGELOG](CHANGELOG.md) pour l'historique des versions.

## ⚖️ Licence & modèle

HELYOS suit un modèle **Open Core** ([ADR-0008](CODEX/ADR/ADR-0008-open-core-business-model.md)) :

- **Le cœur** (kernel, gouvernance A0–A5, API de base, SDK) est **open source sous [AGPL-3.0](LICENSE)**.
- Une **licence commerciale** (dual-licensing) est disponible pour les usages qui ne peuvent pas
  se conformer à l'AGPL, ainsi que des **modules Pro/Enterprise** propriétaires.
- Détails : [business model](CODEX/05_ECONOMIE/01_Business_Model.md) · [frontière open/Pro](CODEX/05_ECONOMIE/02_Frontiere_Open_Core.md).

> Copyright © 2026 Le Conservateur (HELYOS). HELYOS est distribué sous licence AGPL-3.0 ;
> voir [`LICENSE`](LICENSE). Pour une licence commerciale, contacter le Conservateur.

*Note : « HELYOS » est sans lien avec le projet homonyme « helyOS » de Fraunhofer IVI — voir [RFC-0003](CODEX/RFC/RFC-0003-arbitrage-du-nom.md).*
