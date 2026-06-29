# Conformité, Propriété Intellectuelle & Risques juridiques

`v0.3` · Statut : **Vivant** · Décision : [ADR-0009](../ADR/ADR-0009-conformite-legale.md)

---

> ⚠️ **Ceci n'est pas un avis juridique.** C'est une cartographie des risques et des mesures
> de prudence standard. **Avant tout lancement commercial, faire valider par un juriste / un
> conseil en PI.** L'objectif : éviter plagiat, contrefaçon et **amendes**.

## 1. Risques de marque (le plus urgent)

| Nom | Risque | Mesure |
|-----|--------|--------|
| **« Jarvis »** | « J.A.R.V.I.S. » est fortement associé à **Marvel/Disney** ; NVIDIA a *renommé* son « Jarvis » en « Riva ». Usage **commercial** = risque de contrefaçon de marque. | **Ne pas utiliser « Jarvis » en public/commercial.** Le garder comme **nom de code interne** au plus. Choisir un nom propre pour la couche incarnée. Voir [RFC-0003](../RFC/RFC-0003-arbitrage-du-nom.md). |
| **« HELYOS » vs « helyOS »** | Projet homonyme (Fraunhofer IVI) dans un **domaine proche** (orchestration/robotique) → confusion, risque de marque. | Vérifier disponibilité (INPI/EUIPO), envisager un distinctif. RFC-0003. |

> **Avant dépôt de marque / communication large** : recherche d'antériorité (INPI en France,
> EUIPO en UE), et vérification des noms de domaine / handles.

## 2. Licences & propriété du code

- **Cœur sous AGPL-3.0** ([ADR-0005](../ADR/ADR-0005-licence.md)).
- **Modules Pro propriétaires** ([helyos-pro], privé). **Légal uniquement** parce que **le
  Conservateur détient 100 % du copyright du cœur** → il peut le ré-utiliser sous d'autres
  termes (dual-licensing). **Si un tiers contribue au cœur sans CLA, ce montage devient
  illégal** (le contributeur garde ses droits sous AGPL).
- **Donc : CLA (Contributor License Agreement) OBLIGATOIRE** pour toute contribution externe
  au cœur. Aucune PR fusionnée sans CLA signé.
- **Ne jamais copier de code tiers sous copyleft (GPL/AGPL/LGPL modifié) dans les modules
  propriétaires.** Vérifier la licence de toute dépendance ajoutée (un ADR par dépendance).

## 3. Plagiat / originalité

- Le code HELYOS est **original** (écrit pour le projet). Les frameworks sont **importés**, pas copiés.
- Le seul texte tiers reproduit verbatim est la **licence AGPL-3.0** (© FSF) — **autorisé** (la FSF
  permet la copie verbatim de sa licence). Voir [THIRD_PARTY_NOTICES](../../THIRD_PARTY_NOTICES.md).
- Veille continue : pas de copier-coller de Stack Overflow / dépôts sous licence incompatible
  sans en vérifier les termes.

## 4. Responsabilité des agents métier (juridique, finance, santé…)

Risque majeur d'**amende / poursuite** : fournir un outil « juridique » ou « financier » sans
réserve peut engager ta responsabilité.

- **Disclaimer obligatoire et visible** sur chaque agent métier : *« Outil d'aide à titre
  informatif. Ne constitue pas un avis juridique / financier / médical. Vérification par un
  professionnel requise. »* (Implémenté dans les agents Pro.)
- **Aucune action irréversible automatique** : la gouvernance A0–A5 + règles d'or l'empêchent
  déjà (ex. **GR-7** : finance jamais autonome).
- Conserver l'**audit** (preuve de la gouvernance appliquée) — atout en cas de litige.

## 5. Données personnelles (RGPD) — pour le SaaS / helyos-cloud

- **Local-first par défaut** = surface RGPD minimale tant que la donnée reste chez l'utilisateur.
- Dès qu'on **héberge** (helyos-cloud) : base légale, **registre des traitements**, DPA avec
  les clients, gestion des droits (accès/effacement), localisation UE des données, durées de
  conservation. À cadrer par RFC **avant** d'ouvrir le SaaS.

## 6. Checklist avant lancement commercial

- [ ] Nom validé (recherche d'antériorité marque + domaines) — abandonner « Jarvis » public.
- [ ] CLA en place pour contributeurs externes.
- [ ] Inventaire des licences de dépendances à jour ([THIRD_PARTY_NOTICES](../../THIRD_PARTY_NOTICES.md)).
- [ ] Disclaimers sur tous les agents métier.
- [ ] CGU / CGV + politique de confidentialité (si SaaS).
- [ ] Conformité RGPD (si traitement de données).
- [ ] Revue par un juriste / conseil PI.
