"""Le World Model d'HELYOS — l'état probabiliste de l'entreprise S_t.

Le LLM n'est plus le système : il devient un *estimateur* qui alimente ce modèle.
Le système, lui, c'est ce graphe de croyances + la fonction d'utilité + la
politique de décision (argmax de l'utilité espérée). Voir RFC-0019.
"""

from .model import Belief, WorldModel
from .decision import Action, Decision as WorldDecision, Policy
from .seed import seed_world

__all__ = ["Belief", "WorldModel", "Action", "WorldDecision", "Policy", "seed_world"]
