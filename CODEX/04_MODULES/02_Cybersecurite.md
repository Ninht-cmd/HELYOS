# Module — Cybersécurité (Blue / Red)

`v0.2` · Statut : **🔧 Cadrage** · Niveau d'autonomie : **A0–A2** (offensif jamais auto)

---

## Objet

Doter HELYOS d'une **posture de sécurité** à deux faces, dans un cadre **strictement défensif et autorisé** :

- **Blue Team (défense)** — durcissement, détection, réponse, sauvegardes, veille de vulnérabilités sur le périmètre **du Conservateur**.
- **Red Team (offensif autorisé)** — tests d'intrusion **uniquement** sur des actifs possédés ou explicitement autorisés, à des fins défensives.

## Principe cardinal de ce module

> La cybersécurité d'HELYOS est **défensive par finalité**. Toute capacité offensive existe pour **renforcer la défense** d'un périmètre autorisé — jamais pour cibler des tiers.

### Interdits absolus (au-delà des règles d'or générales)

- ❌ Aucune action offensive contre un système **non possédé / non autorisé par écrit**.
- ❌ Aucune capacité de **DoS**, de ciblage de masse, de compromission de chaîne d'approvisionnement, ou d'évasion de détection à finalité malveillante.
- ❌ Aucune exfiltration de données.
- ✅ Red Team **toujours** en **A2 (validation humaine)** minimum, sur périmètre déclaré, avec autorisation traçée.

## Garde-fous de gouvernance

| Activité | Niveau | Condition |
|----------|:------:|-----------|
| Scan de posture (lecture) sur actifs propres | A0–A1 | Périmètre déclaré |
| Recommandations de durcissement | A1 | — |
| Application d'un correctif / config | A2 | Validation + sauvegarde (GR-1) |
| Test offensif autorisé | A2 | **Autorisation écrite + périmètre + fenêtre** |
| Réponse à incident (action) | A2 | Validation, sauf garde-fous A3 pré-approuvés |

## Roadmap cybersécurité (esquisse)

1. **Inventaire & posture** — cartographier les actifs du Conservateur (Blue, A0).
2. **Sauvegardes vérifiables** — socle de GR-1 (pas de suppression sans backup).
3. **Détection** — journaux, alertes, intégration observabilité (Loki/Grafana).
4. **Veille de vulnérabilités** — flux CVE pertinents au périmètre.
5. **Tests autorisés** — Red Team encadrée, sur actifs propres uniquement.

## Lien gouvernance

Ce module est le **cas d'usage le plus sensible** d'HELYOS : il illustre pourquoi la [gouvernance A0–A5](../03_GOUVERNANCE/00_Autonomie_A0_A5.md) et les [règles d'or](../03_GOUVERNANCE/01_Regles_Or.md) sont codées et testées. Une capacité de sécurité sans gouvernance exécutée serait un risque, pas un atout.
