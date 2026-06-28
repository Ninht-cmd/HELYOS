"""Jarvis Kernel — le cœur exécutable d'HELYOS.

Jarvis = Kernel + Mémoire + Agents + Outils + Gouvernance + Observabilité.

Le cœur (bus, gouvernance, mémoire, agents) ne dépend que de la bibliothèque
standard : il démarre et se teste sans aucun service externe (Local First, ADN 2).
La couche API (FastAPI) est optionnelle — voir ``jarvis_kernel.main``.

Source de vérité : ../../CODEX
"""

__version__ = "0.2.0"
__all__ = ["__version__"]
