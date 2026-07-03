"""Business — HELYOS GÈRE un portefeuille de business (pas juste en créer un).

Le kernel devient l'orchestrateur : il tient l'état, les métriques et les tâches de
chaque business (ex. boutique Shopify, chaîne YouTube, HELYOS open-source…), et toute
action sur le monde réel passe par la gouvernance. Honnête : il *gère l'information et
propose/exécute des actions gouvernées* ; il ne rend pas les business rentables tout seul.
"""

from .portfolio import Business, BusinessPortfolio, seed_known_businesses

__all__ = ["Business", "BusinessPortfolio", "seed_known_businesses"]
