# Accès à HELYOS — les trois niveaux, sans promesse

« Une appli locale » : c'est vrai aujourd'hui, et c'est en partie un **choix**
(Local First, ADR-0002) — tes données restent sur ta machine, zéro coût, zéro
service tiers. Mais « local » ne doit pas vouloir dire « prisonnier de ton PC ».
Voici la vérité sur qui peut y accéder, et à quel prix.

| Niveau | Qui peut l'ouvrir | Comment | Ce que ça coûte / exige |
|---|---|---|---|
| **1. Local** (par défaut) | toi, sur ce PC | `.\scripts\dev.ps1 run` | rien. Le plus sûr. |
| **2. Tes appareils** | toi, sur ton wifi (téléphone, tablette) | `.\scripts\acces_reseau.ps1` | rien. ⚠ pas d'auth : wifi de confiance uniquement. |
| **3. Tout le monde, partout** | n'importe qui, sur Internet | *pas encore possible* | **authentification + hébergement** — un vrai chantier (voir plus bas). |

## Niveau 2 — ton téléphone, maintenant (2 minutes)

1. Ton téléphone et ton PC sur le **même wifi**.
2. Sur le PC : `.\scripts\acces_reseau.ps1`
3. Le script affiche une URL `http://192.168.x.x:8080/app/` — ouvre-la sur ton
   téléphone. Ajoute-la à l'écran d'accueil (Safari → Partager → « Sur l'écran
   d'accueil ») : HELYOS devient une **app plein écran** sur ton iPhone (PWA).

C'est déjà « pas seulement sur mon PC ». Mais ça reste chez toi — ce qui est bien,
car le noyau n'a pas encore de serrure.

## Niveau 3 — « tout le monde » : ce que ça exige vraiment

Rendre HELYOS accessible à n'importe qui sur Internet n'est **pas** une case à
cocher — et te le vendre comme tel serait malhonnête. Aujourd'hui le noyau est
**grand ouvert** : aucune authentification. Le publier tel quel, ce serait donner
à n'importe qui les clés de ton portefeuille et de ta caisse.

Avant « tout le monde », il faut, dans l'ordre :

1. **Authentification** — comptes, mots de passe (jamais en clair), sessions.
   C'est LA brique manquante, et c'est du sérieux (sécurité = on ne bâcle pas).
2. **Isolation par utilisateur** — le portefeuille d'Alice invisible pour Bob.
   Le noyau est aujourd'hui mono-utilisateur ; ça se re-conçoit, ça ne se rustine pas.
3. **Hébergement** — un serveur (VPS ~5–10 €/mois), un domaine, HTTPS.
4. **Conformité** — RGPD dès que les données de tiers entrent en jeu (ADR-0009).

C'est exactement le palier **v10** de la Constitution 2050 : « infrastructure pour
d'autres fondateurs ». Le dépôt `helyos-cloud` en pose déjà le tout premier jalon
(passerelle + serveur de licence). Mais ce niveau se **finance**, il ne se code pas
en une nuit : c'est ce que les premiers revenus paient (RFC-0008).

## En résumé honnête

- « Sur mon téléphone » : ✅ disponible ce soir (niveau 2).
- « Tout le monde peut l'utiliser » : 🔧 chantier réel — auth d'abord, puis
  hébergement, puis multi-utilisateur. Financé par les premiers clients, pas avant.

Un produit que tout le monde utilise commence toujours par un produit qu'**une**
personne utilise vraiment. Cette personne, c'est toi. Le reste vient après le
premier euro.
