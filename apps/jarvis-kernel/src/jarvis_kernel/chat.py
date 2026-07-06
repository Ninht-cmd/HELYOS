"""`python -m jarvis_kernel.chat` — parle à HELYOS en langage naturel.

Le « moment Jarvis » : une seule invite, une seule intelligence. Tu écris, HELYOS
comprend l'intention, route vers la bonne capacité, agit SOUS gouvernance, et répond —
en affichant le verdict quand une décision de gouvernance a eu lieu (le refus fait
partie de la réponse). Local First : StubLLM par défaut, vrai modèle si Ollama est câblé.
"""

from __future__ import annotations

import sys

from .governance.autonomy import AutonomyLevel
from .jarvis import Jarvis, JarvisReply, build_jarvis

_BADGE = {"allow": "✓ autorisé", "require_validation": "⏸ validation requise", "deny": "✗ refusé"}


def render(reply: JarvisReply) -> str:
    """Rend une réponse pour le terminal (testable, sans effet de bord)."""
    lines = [f"HELYOS › {reply.text}"]
    if reply.governed and reply.decision:
        badge = _BADGE.get(reply.decision, reply.decision)
        tag = f"   [{badge}"
        if reply.rule:
            tag += f" · {reply.rule}"
        lines.append(tag + f" · intention: {reply.intent}]")
    return "\n".join(lines)


def run(jarvis: Jarvis | None = None, granted: AutonomyLevel = AutonomyLevel.A1) -> None:  # pragma: no cover
    """Boucle interactive. Ctrl-C ou 'exit' pour quitter."""
    jarvis = jarvis or build_jarvis()
    backend = type(jarvis.llm).__name__
    print(f"HELYOS — intelligence gouvernée locale (LLM: {backend}, niveau: {granted.name}).")
    print("Parle-moi. 'exit' pour quitter.\n")
    while True:
        try:
            msg = input("toi › ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nHELYOS › À bientôt, Conservateur.")
            return
        if not msg:
            continue
        if msg.lower() in {"exit", "quit", "q"}:
            print("HELYOS › À bientôt, Conservateur.")
            return
        print(render(jarvis.handle(msg, granted=granted)) + "\n")


def main() -> None:  # pragma: no cover
    run()


if __name__ == "__main__":
    sys.exit(main())
