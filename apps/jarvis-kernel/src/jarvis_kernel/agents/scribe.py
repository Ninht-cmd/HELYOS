"""ScribeAgent — le premier agent utile d'HELYOS (voir RFC-0002).

Friction supprimée (ADN 14, 16) : « les décisions importantes se perdent dans les
conversations » et « écrire le boilerplate d'un ADR est fastidieux ». Le Scribe
transforme une décision en un fichier ADR correctement formaté.

Gouvernance : écrire un fichier = ``WRITE_LOCAL`` = A2. L'action passe TOUJOURS par
la gouvernance avant d'être exécutée ; sans niveau A2 (ou validation), elle reste en
attente de validation humaine. C'est la démonstration vivante du flux gouverné.
"""

from __future__ import annotations

import re
import time
from pathlib import Path
from typing import Any

from ..governance.autonomy import AutonomyLevel
from ..governance.policy import Action, ActionType, Decision, PolicyVerdict
from ..governance.service import GovernanceService
from ..memory.store import MemoryStore
from ..observability.telemetry import get_logger
from ..observability.tracing import span
from .base import Agent

logger = get_logger(__name__)


def _slug(title: str) -> str:
    s = re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")
    return s or "decision"


def render_adr(
    number: int,
    title: str,
    context: str,
    decision: str,
    consequences: str = "",
    adn: str = "",
    status: str = "Proposed",
    date: str | None = None,
) -> str:
    """Rend un ADR au format du Codex (CODEX/ADR/_template.md)."""
    date = date or time.strftime("%Y-%m-%d")
    return f"""# ADR-{number:04d} — {title}

- **Statut** : {status}
- **Date** : {date}
- **Décideur(s)** : Le Conservateur
- **Principes ADN engagés** : {adn or "—"}
- **Rédigé par** : ScribeAgent (proposé ; à valider par le Conservateur)

## Contexte

{context}

## Décision

{decision}

## Conséquences

{consequences or "- À compléter."}
"""


class ScribeAgent(Agent):
    name = "scribe"
    description = "Transforme une décision en fichier ADR formaté (écriture = A2)."
    required_level = AutonomyLevel.A2

    def propose(self, context: dict[str, Any]) -> Action:
        """Propose l'action d'écriture d'un ADR (non exécutée tant que non autorisée)."""
        number = int(context.get("number", 0))
        title = str(context.get("title", "décision sans titre"))
        target = f"CODEX/ADR/ADR-{number:04d}-{_slug(title)}.md"
        return Action(
            type=ActionType.WRITE_LOCAL,
            description=f"Créer l'ADR « {title} »",
            target=target,
            actor=self.name,
            validated=bool(context.get("validated", False)),
            metadata={"number": number, "title": title},
        )

    def draft_adr(
        self,
        governance: GovernanceService,
        *,
        number: int,
        title: str,
        context: str,
        decision: str,
        consequences: str = "",
        adn: str = "",
        granted: AutonomyLevel,
        adr_dir: str | Path,
        validated: bool = False,
        memory: MemoryStore | None = None,
    ) -> tuple[PolicyVerdict, Path | None]:
        """Soumet l'écriture à la gouvernance ; si autorisée, écrit le fichier ADR.

        Retourne (verdict, chemin_écrit | None). Si le verdict n'est pas ALLOW,
        rien n'est écrit (l'action reste en attente de validation ou refusée).
        """
        with span("scribe.draft_adr", **{"helyos.adr_number": number, "helyos.title": title}):
            action = self.propose(
                {"number": number, "title": title, "validated": validated}
            )
            verdict = governance.submit(action, granted)

            if verdict.decision is not Decision.ALLOW:
                logger.info(
                    "ADR non écrit (gouvernance)",
                    extra={"context": {"decision": verdict.decision.value,
                                       "rule": verdict.rule, "title": title}},
                )
                return verdict, None

            adr_dir = Path(adr_dir)
            adr_dir.mkdir(parents=True, exist_ok=True)
            path = adr_dir / f"ADR-{number:04d}-{_slug(title)}.md"
            path.write_text(
                render_adr(number, title, context, decision, consequences, adn),
                encoding="utf-8",
            )

            if memory is not None:
                memory.remember(
                    f"ADR-{number:04d}",
                    {"title": title, "path": str(path), "ts": time.time()},
                    namespace="decisions",
                )

            governance.bus.emit("scribe.adr_written", number=number, title=title, path=str(path))
            logger.info("ADR écrit", extra={"context": {"path": str(path), "title": title}})
            return verdict, path

    def index_codex(
        self,
        governance: GovernanceService,
        memory: MemoryStore,
        codex_dir: str | Path,
        granted: AutonomyLevel = AutonomyLevel.A0,
    ) -> int:
        """Indexe le Codex (lecture = A0) dans la mémoire persistante. Retourne le nb de docs.

        Sert l'ADN 15 (« relire le Codex avant toute stratégie ») : rend le Codex
        interrogeable. La lecture passe par la gouvernance pour être auditée.
        """
        with span("scribe.index_codex"):
            read = Action(
                type=ActionType.READ, description="Indexer le Codex", actor=self.name
            )
            verdict = governance.submit(read, granted)
            if verdict.decision is not Decision.ALLOW:
                return 0

            codex_dir = Path(codex_dir)
            count = 0
            for md in sorted(codex_dir.rglob("*.md")):
                rel = md.relative_to(codex_dir).as_posix()
                try:
                    text = md.read_text(encoding="utf-8")
                except Exception:
                    continue
                memory.remember(rel, text, namespace="codex")
                count += 1
            governance.bus.emit("scribe.codex_indexed", documents=count)
            logger.info("Codex indexé", extra={"context": {"documents": count}})
            return count
