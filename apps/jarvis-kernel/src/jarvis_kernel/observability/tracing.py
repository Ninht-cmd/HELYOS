"""Tracing distribué — OpenTelemetry → OTLP (Langfuse / Grafana Tempo).

Tout est observable (ADN 6). Le tracing est OPTIONNEL et dégradé en no-op si
OpenTelemetry n'est pas installé ou s'il est désactivé : le cœur reste sans
dépendance (Local First). Activation : ``HELYOS_OTEL_ENABLED=1`` + endpoint OTLP.

Langfuse : expose un endpoint OTLP ; pointer ``HELYOS_OTEL_ENDPOINT`` vers lui
(et fournir les en-têtes d'auth via OTEL_EXPORTER_OTLP_HEADERS) suffit à recevoir
les traces — voir CODEX/07_TECH.
"""

from __future__ import annotations

from contextlib import contextmanager
from typing import Any, Iterator

from .telemetry import get_logger

logger = get_logger(__name__)

_tracer: Any | None = None
_enabled = False


def setup_tracing(
    enabled: bool = False,
    endpoint: str = "http://localhost:4318",
    service_name: str = "helyos-jarvis-kernel",
) -> bool:
    """Initialise OpenTelemetry si demandé ET disponible. Retourne l'état effectif."""
    global _tracer, _enabled
    if not enabled:
        logger.info("Tracing désactivé (no-op)", extra={"context": {"otel": False}})
        _enabled = False
        return False
    try:
        from opentelemetry import trace
        from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
        from opentelemetry.sdk.resources import Resource
        from opentelemetry.sdk.trace import TracerProvider
        from opentelemetry.sdk.trace.export import BatchSpanProcessor
    except ImportError:
        logger.info(
            "OpenTelemetry absent : tracing en no-op. "
            "Installer la couche serveur+otel pour l'activer.",
            extra={"context": {"otel": "missing"}},
        )
        _enabled = False
        return False

    provider = TracerProvider(resource=Resource.create({"service.name": service_name}))
    provider.add_span_processor(
        BatchSpanProcessor(OTLPSpanExporter(endpoint=f"{endpoint.rstrip('/')}/v1/traces"))
    )
    trace.set_tracer_provider(provider)
    _tracer = trace.get_tracer("helyos.jarvis-kernel")
    _enabled = True
    logger.info(
        "Tracing OpenTelemetry actif",
        extra={"context": {"otel": True, "endpoint": endpoint, "service": service_name}},
    )
    return True


@contextmanager
def span(name: str, **attributes: Any) -> Iterator[None]:
    """Ouvre un span s'il y a un tracer ; sinon ne fait rien (no-op)."""
    if _tracer is None:
        yield
        return
    with _tracer.start_as_current_span(name) as sp:  # pragma: no cover - dépend d'OTel
        for k, v in attributes.items():
            try:
                sp.set_attribute(k, v)
            except Exception:
                pass
        yield


def is_enabled() -> bool:
    return _enabled
