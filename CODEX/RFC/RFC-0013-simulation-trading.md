# RFC-0013 — Trading en simulation : la seule réponse honnête à « HELYOS investit »

- **Statut** : Accepted
- **Date** : 2026-07-11
- **Auteur** : Le Conservateur
- **Principes ADN engagés** : 3 (gouvernance), 8 (honnêteté), 16 (revenu d'abord)

## Le problème

Le fondateur demande : « ça ne génère pas d'argent, ne génère pas de business,
n'investit pas — je veux que ça fasse tout ça. » La vérité structurante, à graver :

**Aucun logiciel ne génère de l'argent seul.** L'argent entre par trois portes —
des clients qui paient, des ventes, des positions de marché — et chacune exige des
comptes au nom du fondateur (Stripe, Printful/Shopify Payments, courtier), du
capital, et sa signature. HELYOS automatise tout le chemin JUSQU'À la porte ;
les serrures sont juridiquement humaines. Quiconque vend le contraire vend du rêve.

## Décision : `PaperTrader` (agent A1)

HELYOS « investit » dès aujourd'hui — **en simulation** : 1 000 € FICTIFS, prix
réels (connecteur `market`), stratégie assumée simple (croisement SMA20/50 + garde
RSI<70, 10 % du cash par position), P&L mesuré sans complaisance.

Invariants (testés) :
- **Aucun ordre réel n'existe, par construction** : pas de courtier, pas de clé,
  et le PaperTrader n'émet JAMAIS d'action FINANCIAL. « investis 100 € » en vrai
  reste GR-7 (validation, toujours).
- L'étiquette « SIMULATION — argent fictif » accompagne chaque affichage.
- Une perte simulée s'affiche comme une perte (testé sur retournement de marché).
- Premier comportement observé en réel : marché baissier → zéro achat. La
  stratégie sait ne rien faire — c'est déjà mieux que la plupart des bots vendus.

Surface : intention Jarvis `simulation_trading` (« lance la simulation »), `GET
/paper`, `POST /paper/step`, veilleur du Pouls (le P&L simulé entre au briefing).

## Le chemin vers l'argent RÉEL (rappel opposable)

| Flux | Ce qui est prêt (code) | Ce qui manque (humain, ~2 h au total) |
|---|---|---|
| Services (Plan Cash, RFC-0008) | agent factures + SMTP gouverné + offre à rédiger | choisir LA niche · lien Stripe (15 min) · clés SMTP |
| E-commerce | boutique + 5 produits brouillon + connecteur Shopify | compte Printful · activer Shopify Payments · jeton API |
| Investissement | simulation (cette RFC) | que la SIMULATION prouve un edge sur la durée ; ENSUITE seulement, RFC courtier (budgets, coupe-circuit, GR-7 à vie) |

La règle de promotion : le PaperTrader ne touchera un euro réel que si son P&L
simulé bat « ne rien faire » sur une période significative, ET après une RFC
dédiée. Un backtest gagnant ne suffit pas (ADR-0010 : PBO/Deflated Sharpe).
