"""Port LLM — abstraction de modèle (non-dépendance, ADN).

Aucun composant ne parle directement à un fournisseur. ``LLMPort`` isole le modèle ;
``StubLLM`` fournit une implémentation déterministe locale (zéro dépendance) pour
tester l'orchestration. Des adaptateurs (LiteLLM → Ollama/cloud, NeMo) se branchent
derrière la même interface — voir CODEX/07_TECH et la fusion (Riva/NeMo).
"""

from __future__ import annotations

from abc import ABC, abstractmethod


class LLMPort(ABC):
    """Contrat minimal d'un modèle de langage."""

    @abstractmethod
    def complete(self, prompt: str, **kwargs) -> str: ...


class StubLLM(LLMPort):
    """LLM déterministe local : pas d'appel réseau, reproductible (mode No-AI friendly)."""

    def __init__(self, prefix: str = "[stub-llm]") -> None:
        self.prefix = prefix

    def complete(self, prompt: str, **kwargs) -> str:
        compact = " ".join(prompt.split())
        head = compact[:160]
        return f"{self.prefix} synthèse: {head}"


class OllamaLLM(LLMPort):  # pragma: no cover - dépend d'un service externe (Ollama)
    """Vrai modèle local via Ollama (API HTTP locale, stdlib uniquement).

    Local First : aucune donnée ne sort de la machine. Pensée désactivée par défaut
    (``/no_think`` + option) pour la latence ; balises ``<think>`` retirées par sécurité.
    """

    def __init__(self, model: str = "qwen3:8b", host: str = "http://localhost:11434",
                 num_predict: int = 128, temperature: float = 0.2,
                 think: bool = False, timeout: int = 120) -> None:
        self.model = model
        self.host = host.rstrip("/")
        self.num_predict = num_predict
        self.temperature = temperature
        self.think = think
        self.timeout = timeout

    def complete(self, prompt: str, **kwargs) -> str:
        import json
        import re
        import urllib.error
        import urllib.request

        body = {
            "model": self.model,
            "prompt": prompt if self.think else ("/no_think\n" + prompt),
            "stream": False,
            "think": self.think,
            "options": {
                "num_predict": int(kwargs.get("num_predict", self.num_predict)),
                "temperature": float(kwargs.get("temperature", self.temperature)),
            },
        }
        req = urllib.request.Request(self.host + "/api/generate",
                                     data=json.dumps(body).encode(),
                                     headers={"content-type": "application/json"}, method="POST")
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as r:
                data = json.loads(r.read().decode())
        except (urllib.error.URLError, OSError) as exc:
            raise RuntimeError(
                f"Ollama injoignable sur {self.host} ({exc}). "
                "Lancer 'ollama serve' et 'ollama pull " + self.model + "'."
            ) from exc
        txt = data.get("response", "")
        return re.sub(r"<think>.*?</think>", "", txt, flags=re.S).strip()


class LiteLLMAdapter(LLMPort):  # pragma: no cover - dépend d'un service externe
    """Adaptateur LiteLLM (optionnel) → Ollama (local) ou API cloud (opt-in).

    Câblé par RFC : route par défaut vers un modèle LOCAL (Local First).
    """

    def __init__(self, model: str = "ollama/llama3") -> None:
        try:
            import litellm  # type: ignore  # noqa: F401
        except ImportError as exc:
            raise RuntimeError(
                "LiteLLMAdapter nécessite 'litellm' (pip install litellm)."
            ) from exc
        self.model = model

    def complete(self, prompt: str, **kwargs) -> str:
        import litellm  # type: ignore

        resp = litellm.completion(
            model=self.model, messages=[{"role": "user", "content": prompt}], **kwargs
        )
        return resp["choices"][0]["message"]["content"]
