# CODEX HELYOS

> Le Codex est la **source de vérité** d'HELYOS. Il prime sur le code, sur la mémoire d'un modèle, et sur toute conversation.
> *« Relire le Codex avant toute stratégie. »*

Ce Codex est **vivant** et **versionné**. Il grandit par accumulation de décisions tracées (ADR/RFC), jamais par réécriture silencieuse. L'objectif à terme : un corpus complet, navigable, qui constitue le patrimoine intellectuel de l'entreprise.

---

## Plan du Codex

| # | Section | Contenu |
|---|---------|---------|
| 00 | [Vision](00_VISION/00_Vision.md) · [Mission](00_VISION/01_Mission.md) · [Manifeste](00_VISION/02_Manifeste.md) | Le *pourquoi* et le cap long terme |
| 01 | [ADN](01_ADN/00_ADN.md) | Les 16 principes fondateurs, non négociables |
| 02 | [Architecture](02_ARCHITECTURE/00_Overview.md) | Modèle C4 : contexte → conteneurs → composants |
| 03 | [Gouvernance](03_GOUVERNANCE/00_Autonomie_A0_A5.md) | Autonomie graduée **A0–A5** + [règles d'or](03_GOUVERNANCE/01_Regles_Or.md) |
| 04 | [Modules](04_MODULES/00_Overview.md) | Les domaines fonctionnels |
| 05 | [Économie](05_ECONOMIE/00_Boucle_Economique.md) | [Boucle](05_ECONOMIE/00_Boucle_Economique.md) · [Business model open-core](05_ECONOMIE/01_Business_Model.md) · [Frontière open/Pro](05_ECONOMIE/02_Frontiere_Open_Core.md) |
| 06 | [Roadmap](06_ROADMAP/00_Roadmap.md) | Les jalons jusqu'à « AGI Ready » |
| 07 | [Tech](07_TECH/00_Stack.md) | La stack de référence |
| 08 | [Écosystème](08_ECOSYSTEME/00_Etat_de_lart.md) | État de l'art (helyOS, NVIDIA Isaac/Riva/NeMo, OpenJarvis) + [fusion HELYOS × Jarvis](02_ARCHITECTURE/05_Fusion_HELYOS_Jarvis.md) |
| 09 | [Légal](09_LEGAL/00_Conformite_IP.md) | Conformité, PI, risques de marque (Jarvis/helyOS), CLA, RGPD, disclaimers |
| — | [ADR](ADR/README.md) | Décisions d'architecture (le *comment* et le *pourquoi* techniques) |
| — | [RFC](RFC/README.md) | Propositions structurantes en discussion |
| — | [Glossaire](GLOSSAIRE.md) | Vocabulaire HELYOS |

## Comment contribuer au Codex

1. **Une idée structurante ?** → ouvre une **[RFC](RFC/_template.md)**.
2. **Une décision technique tranchée ?** → écris un **[ADR](ADR/_template.md)** (immuable une fois `Accepted`).
3. **Une clarification de vision/ADN ?** → édite la section concernée, et référence la décision en bas de page.

> Règle d'intégrité : **toute** affirmation forte du Codex doit pouvoir être reliée à une RFC, un ADR, ou un principe de l'ADN. Pas d'orphelin.

## Hiérarchie d'autorité (en cas de conflit)

```
ADN  >  Vision/Mission  >  ADR acceptés  >  Architecture  >  Code
```

Si le code contredit le Codex, **c'est le code qui a tort**.
