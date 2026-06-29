"""Point d'entrée de l'API du Kernel (FastAPI).

Lancer :
    uvicorn jarvis_kernel.main:app --host 127.0.0.1 --port 8080
ou :
    python -m jarvis_kernel

La couche API est optionnelle (FastAPI requis). Le cœur fonctionne sans elle.
"""

from __future__ import annotations

from .context import build_default_context
from .observability.telemetry import get_logger

logger = get_logger(__name__)


def create_app():
    """Construit l'application FastAPI et câble le contexte du Kernel."""
    from fastapi import FastAPI  # import local : ne charge FastAPI que si on crée l'app
    from fastapi.responses import HTMLResponse

    from .api.dashboard import DASHBOARD_HTML
    from .api.routes import router

    ctx = build_default_context()
    app = FastAPI(
        title=ctx.settings.app_name,
        version=ctx.settings.version,
        description=(
            "Kernel Jarvis — le cœur gouverné d'HELYOS. "
            "Source de vérité : le CODEX. Toute action passe par la gouvernance A0–A5."
        ),
    )
    app.state.kernel = ctx
    app.include_router(router)

    @app.get("/", response_class=HTMLResponse, tags=["kernel"], include_in_schema=False)
    def root() -> str:
        """Tableau de bord HTML (page d'accueil humaine)."""
        return DASHBOARD_HTML

    @app.get("/info", tags=["kernel"])
    def info() -> dict:
        return {
            "name": ctx.settings.app_name,
            "version": ctx.settings.version,
            "codex": "Le Codex est la source de vérité.",
            "docs": "/docs",
            "endpoints": ["/health", "/agents", "/intent", "/governance/levels",
                          "/governance/audit", "/events"],
        }

    logger.info(
        "Kernel prêt",
        extra={"context": {"app": ctx.settings.app_name, "version": ctx.settings.version,
                           "agents": len(ctx.registry)}},
    )
    return app


# Application ASGI exposée pour uvicorn.
app = create_app()
