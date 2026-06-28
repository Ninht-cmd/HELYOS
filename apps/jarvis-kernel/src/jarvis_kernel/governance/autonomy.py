"""Autonomie graduée A0–A5.

Source de vérité : CODEX/03_GOUVERNANCE/00_Autonomie_A0_A5.md

L'autonomie n'est jamais binaire. ``IntEnum`` donne un ordre total : on peut
comparer ``granted >= required`` directement.
"""

from __future__ import annotations

from enum import IntEnum


class AutonomyLevel(IntEnum):
    """Les six niveaux d'autonomie. Un niveau supérieur inclut les inférieurs."""

    A0 = 0  # Lecture       — observer, lire. Aucune écriture, aucune action.
    A1 = 1  # Préparation   — simuler, proposer, brouillonner. Rien appliqué.
    A2 = 2  # Exécution validée — agir après accord humain explicite (par action).
    A3 = 3  # Faible risque — agir seul sur des actions réversibles, faible enjeu.
    A4 = 4  # Gestion contrôlée — gérer un périmètre délimité dans des garde-fous.
    A5 = 5  # Stratégique   — agir sur la vision long terme, cadré par le Codex.

    @property
    def label(self) -> str:
        return {
            AutonomyLevel.A0: "Lecture",
            AutonomyLevel.A1: "Préparation",
            AutonomyLevel.A2: "Exécution avec validation",
            AutonomyLevel.A3: "Exécution faible risque",
            AutonomyLevel.A4: "Gestion contrôlée",
            AutonomyLevel.A5: "Autonomie stratégique",
        }[self]

    @classmethod
    def from_name(cls, name: str) -> "AutonomyLevel":
        """``"A2"`` ou ``"2"`` -> AutonomyLevel.A2. Défaut sûr : A1."""
        key = (name or "").strip().upper()
        if key.startswith("A") and key[1:].isdigit():
            key = key[1:]
        if key.isdigit() and 0 <= int(key) <= 5:
            return cls(int(key))
        return cls.A1  # défaut bas et sûr (jamais A5 par défaut)

    def __str__(self) -> str:  # pragma: no cover - cosmétique
        return f"{self.name} ({self.label})"
