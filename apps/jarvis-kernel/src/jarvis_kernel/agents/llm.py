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
