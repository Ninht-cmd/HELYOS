"""HELYOS — Mémoire long terme unifiée (brique #1).

Deux couches, jamais une simple base vectorielle :
  • RELATIONNELLE : la vérité structurée (objectif, date, agent, action, statut, source,
    confiance, gouvernance, validation humaine, résultat réel, liens).
  • VECTORIELLE : retrouver des situations similaires par le SENS (cosinus sac-de-mots).

Cinq objets seulement : MemoryEvent, Episode, DecisionRecord, OutcomeRecord, MemoryLink.

Règle d'or de la mémoire : séparer « ce qui s'est passé » de « ce qu'HELYOS croit
savoir ». Une proposition d'agent n'est JAMAIS une vérité permanente — d'où les statuts :
observed · inferred · proposed · validated · executed · confirmed · superseded · rejected.
"""

from __future__ import annotations

import time
from dataclasses import asdict, dataclass, field

from ..memory.vector import NaiveVectorMemory

STATUSES = ("observed", "inferred", "proposed", "validated", "executed",
            "confirmed", "superseded", "rejected")


@dataclass
class MemoryEvent:
    id: str
    ts: float
    event_type: str            # observation|objective|plan|decision|governance|validation|outcome|learning
    objective_id: str
    agent: str
    content: str
    status: str = "observed"
    confidence: float = 0.5
    sources: list = field(default_factory=list)
    governance: dict = field(default_factory=dict)
    entities: list = field(default_factory=list)


@dataclass
class Episode:
    id: str
    ts: float
    objective: str
    status: str = "open"       # open | closed
    event_ids: list = field(default_factory=list)


@dataclass
class DecisionRecord:
    id: str
    objective_id: str
    ts: float
    agent: str
    content: str
    status: str = "proposed"
    confidence: float = 0.5
    sources: list = field(default_factory=list)
    governance: dict = field(default_factory=dict)
    entities: list = field(default_factory=list)
    reason: str = ""           # motif humain lors de validation/refus
    outcome_id: str = ""


@dataclass
class OutcomeRecord:
    id: str
    decision_id: str
    ts: float
    observed: float
    expected: float
    note: str = ""


@dataclass
class MemoryLink:
    src: str
    rel: str
    dst: str


class UnifiedMemory:
    def __init__(self, clock=None) -> None:
        self._clock = clock or time.time
        self._seq = 0
        self.episodes: dict[str, Episode] = {}
        self.events: dict[str, MemoryEvent] = {}
        self.decisions: dict[str, DecisionRecord] = {}
        self.outcomes: dict[str, OutcomeRecord] = {}
        self.links: list[MemoryLink] = []
        self.vector = NaiveVectorMemory()

    def _id(self, pfx: str) -> str:
        self._seq += 1
        return f"{pfx}-{self._seq:04d}"

    # ---- écriture (le cycle complet) ----
    def start_episode(self, objective: str) -> str:
        oid = self._id("OBJ")
        self.episodes[oid] = Episode(oid, self._clock(), objective)
        self.vector.add(oid, objective, {"type": "objective", "objective_id": oid})
        return oid

    def record_event(self, event_type: str, objective_id: str, agent: str, content: str, *,
                     status: str = "observed", confidence: float = 0.5, sources=None,
                     governance=None, entities=None) -> str:
        eid = self._id("EV")
        ev = MemoryEvent(eid, self._clock(), event_type, objective_id, agent, content, status,
                         confidence, list(sources or []), dict(governance or {}), list(entities or []))
        self.events[eid] = ev
        if objective_id in self.episodes:
            self.episodes[objective_id].event_ids.append(eid)
        self.vector.add(eid, content, {"type": "event", "objective_id": objective_id, "status": status})
        return eid

    def record_decision(self, objective_id: str, agent: str, content: str, *, status: str = "proposed",
                        confidence: float = 0.5, sources=None, governance=None, entities=None) -> str:
        did = self._id("DEC")
        self.decisions[did] = DecisionRecord(did, objective_id, self._clock(), agent, content, status,
                                             confidence, list(sources or []), dict(governance or {}),
                                             list(entities or []))
        self.vector.add(did, content, {"type": "decision", "objective_id": objective_id})
        return did

    def set_decision_status(self, decision_id: str, status: str, reason: str = "") -> None:
        d = self.decisions[decision_id]
        d.status, d.reason = status, reason
        self.record_event("validation", d.objective_id, "human", f"{status}: {d.content}",
                          status=status, entities=d.entities)

    def record_outcome(self, decision_id: str, observed: float, expected: float, note: str = "") -> str:
        oid = self._id("OUT")
        self.outcomes[oid] = OutcomeRecord(oid, decision_id, self._clock(), observed, expected, note)
        self.decisions[decision_id].outcome_id = oid
        return oid

    def link(self, src: str, rel: str, dst: str) -> None:
        self.links.append(MemoryLink(src, rel, dst))

    # ---- lecture (interrogée par le Planner AVANT de planifier) ----
    def retrieve(self, objective: str, *, k: int = 6, threshold: float = 0.05) -> dict:
        hits = self.vector.search(objective, limit=k * 3)
        sim_obj_ids = {h.metadata.get("objective_id") for h in hits if h.score >= threshold}
        sim_obj_ids.discard(None)
        rel = lambda d: (d.objective_id in sim_obj_ids)
        rejected = [self._d(d) for d in self.decisions.values() if d.status == "rejected" and rel(d)]
        validated = [self._d(d) for d in self.decisions.values()
                     if d.status in ("validated", "executed", "confirmed") and rel(d)]
        tried = [self._d(d) for d in self.decisions.values() if d.status == "proposed" and rel(d)]
        similar = [{"objective": self.episodes[o].objective, "objective_id": o}
                   for o in sim_obj_ids if o in self.episodes]
        return {"similar_objectives": similar, "rejected": rejected, "validated": validated,
                "tried": tried, "has_history": bool(similar)}

    @staticmethod
    def _d(d: DecisionRecord) -> dict:
        out = {"content": d.content, "status": d.status, "reason": d.reason,
               "entities": d.entities, "confidence": d.confidence}
        return out

    def summary(self) -> dict:
        from collections import Counter
        return {"episodes": len(self.episodes), "events": len(self.events),
                "decisions": len(self.decisions), "outcomes": len(self.outcomes),
                "by_status": dict(Counter(d.status for d in self.decisions.values()))}

    # ---- persistance ----
    def to_dict(self) -> dict:
        return {"seq": self._seq,
                "episodes": [asdict(e) for e in self.episodes.values()],
                "events": [asdict(e) for e in self.events.values()],
                "decisions": [asdict(d) for d in self.decisions.values()],
                "outcomes": [asdict(o) for o in self.outcomes.values()],
                "links": [asdict(l) for l in self.links]}

    @classmethod
    def from_dict(cls, data: dict) -> "UnifiedMemory":
        m = cls()
        m._seq = data.get("seq", 0)
        for e in data.get("episodes", []):
            m.episodes[e["id"]] = Episode(**e)
            m.vector.add(e["id"], e["objective"], {"type": "objective", "objective_id": e["id"]})
        for e in data.get("events", []):
            m.events[e["id"]] = MemoryEvent(**e)
            m.vector.add(e["id"], e["content"], {"type": "event", "objective_id": e["objective_id"]})
        for d in data.get("decisions", []):
            m.decisions[d["id"]] = DecisionRecord(**d)
            m.vector.add(d["id"], d["content"], {"type": "decision", "objective_id": d["objective_id"]})
        for o in data.get("outcomes", []):
            m.outcomes[o["id"]] = OutcomeRecord(**o)
        m.links = [MemoryLink(**l) for l in data.get("links", [])]
        return m
