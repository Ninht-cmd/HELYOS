"""Registre de modules à interrupteur — allumer/éteindre les capacités à la demande.

Le fondateur veut un on/off par capacité « pour ne pas saturer ». Deux familles :

- INTERNES : les capacités de HELYOS qui consomment des ressources (marché =
  appels réseau Binance, github = appels API, simulation…). Les éteindre allège
  vraiment : le Pouls ne les sonde plus.
- EXTERNES : les vrais outils open-source déjà clonés sur le disque (AnythingLLM,
  ToolJet, Metabase…). Les « allumer » déclare qu'on veut s'en servir ; HELYOS
  sonde alors s'ils tournent réellement (port), et sinon donne la commande pour
  les lancer. On ne prétend jamais qu'un service tourne s'il ne répond pas.

Honnêteté : allumer un module externe ne démarre pas magiquement le logiciel
(chacun a ses dépendances/Docker) — ça l'active dans HELYOS et surface comment
le lancer. Rien de lourd ne tourne tant que tu ne l'as pas allumé.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field

from ..memory.store import MemoryStore

_NS = "modules"


@dataclass
class Module:
    key: str
    name: str
    kind: str                 # finance | data | agent | erp | interne...
    source: str               # 'interne' (capacité HELYOS) | 'local' (repo cloné)
    default_on: bool = True
    path: str = ""            # emplacement du repo cloné (external)
    url: str = ""             # port HTTP du service, s'il en expose un
    launch: str = ""          # comment le lancer (external)
    note: str = ""

    def to_dict(self, enabled: bool) -> dict:
        d = asdict(self)
        d["enabled"] = enabled
        return d


_LAB = r"C:\Users\emezr\WORKSPACE\OPEN-SOURCE-LAB\github"

# Curaté : les capacités internes qui pèsent + les 6 outils locaux réellement utiles.
# (Pas les 1379 repos : la plupart ne sont pas des services qu'on branche.)
DEFAULTS: list[Module] = [
    # --- internes (éteindre = alléger HELYOS) ---
    Module("market", "Marché (Binance)", "finance", "interne", True,
           note="lecture de prix ; appels réseau — éteindre allège le Pouls"),
    Module("github", "GitHub (étoiles)", "data", "interne", True,
           note="lecture publique du repo ; appels API"),
    Module("paper", "Simulation trading", "finance", "interne", False,
           note="portefeuille fictif ; off par défaut"),
    Module("advisory", "Comité C-suite", "agent", "interne", True,
           note="12 conseillers ; utilise le LLM local"),
    # --- externes (repos clonés ; allumer = déclarer usage + sonder le port) ---
    Module("anythingllm", "AnythingLLM", "agent", "local", False,
           path=_LAB + r"\Mintplex-Labs\anything-llm", url="http://127.0.0.1:3001",
           launch="docker compose up -d (dans le dossier docker/ du repo)",
           note="assistant local-first ; le plus pertinent pour HELYOS"),
    Module("tooljet", "ToolJet", "data", "local", False,
           path=_LAB + r"\ToolJet\ToolJet", url="http://127.0.0.1:8082",
           launch="docker run tooljet/tooljet", note="constructeur d'outils internes / dashboards"),
    Module("metabase", "Metabase", "data", "local", False,
           path=_LAB + r"\metabase\metabase", url="http://127.0.0.1:3000",
           launch="docker run -p 3000:3000 metabase/metabase", note="BI / analytics"),
    Module("metagpt", "MetaGPT", "agent", "local", False,
           path=_LAB + r"\FoundationAgents\MetaGPT",
           launch="pip install metagpt puis CLI", note="framework multi-agents"),
    Module("litellm", "LiteLLM", "agent", "local", False,
           path=_LAB + r"\BerriAI\litellm", url="http://127.0.0.1:4000",
           launch="litellm --config config.yaml", note="passerelle LLM unifiée"),
    Module("dolibarr", "Dolibarr", "erp", "local", False,
           path=_LAB + r"\Dolibarr\dolibarr", url="http://127.0.0.1:8083",
           launch="docker run dolibarr/dolibarr", note="ERP/CRM : devis, factures, clients"),
]
_BY_KEY = {m.key: m for m in DEFAULTS}


def _probe(url: str, timeout: float = 1.0) -> bool:
    import urllib.request

    try:
        urllib.request.urlopen(url, timeout=timeout)  # noqa: S310 (url locale de config)
        return True
    except Exception as exc:                          # 4xx/5xx = le service répond quand même
        return "HTTP Error" in type(exc).__name__ or hasattr(exc, "code")


class ModuleRegistry:
    def __init__(self, memory: MemoryStore) -> None:
        self.memory = memory

    def _states(self) -> dict:
        return dict(self.memory.recall("states", namespace=_NS) or {})

    def is_on(self, key: str) -> bool:
        states = self._states()
        if key in states:
            return bool(states[key])
        m = _BY_KEY.get(key)
        return m.default_on if m else False

    def toggle(self, key: str, on: bool) -> Module:
        if key not in _BY_KEY:
            raise KeyError(f"module inconnu : {key!r}")
        states = self._states()
        states[key] = bool(on)
        self.memory.remember("states", states, namespace=_NS)
        return _BY_KEY[key]

    def list(self, probe: bool = False) -> list[dict]:
        out = []
        for m in DEFAULTS:
            enabled = self.is_on(m.key)
            d = m.to_dict(enabled)
            if m.source == "local" and enabled and probe and m.url:
                d["running"] = _probe(m.url)     # sonde réelle : tourne ou pas
            out.append(d)
        return out

    def active_keys(self) -> list[str]:
        return [m.key for m in DEFAULTS if self.is_on(m.key)]

    def summary(self) -> dict:
        allm = self.list()
        on = [m for m in allm if m["enabled"]]
        return {"total": len(allm), "actifs": len(on),
                "actifs_noms": [m["name"] for m in on]}
