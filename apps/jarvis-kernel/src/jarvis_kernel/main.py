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
    from pathlib import Path

    from fastapi import FastAPI  # import local : ne charge FastAPI que si on crée l'app
    from fastapi.responses import HTMLResponse, RedirectResponse
    from fastapi.staticfiles import StaticFiles

    from .api.dashboard import DASHBOARD_HTML
    from .api.routes import router

    ctx = build_default_context()

    # Le serveur expose l'état réel du portefeuille ; on l'amorce une seule fois
    # (les statuts amorcés sont honnêtes : revenus à 0, tâches humaines bloquantes).
    if not ctx.portfolio.list():
        from .business.portfolio import seed_known_businesses
        seed_known_businesses(ctx.portfolio)

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

    web_dir = Path(__file__).resolve().parents[2] / "web"

    if web_dir.is_dir():
        # Interface immersive (WebGL) servie en statique sous /app.
        app.mount("/app", StaticFiles(directory=str(web_dir), html=True), name="web")

        @app.get("/", include_in_schema=False)
        def root():
            return RedirectResponse(url="/app/")
    else:  # repli : pas de dossier web (ex. install minimale)
        @app.get("/", response_class=HTMLResponse, include_in_schema=False)
        def root() -> str:
            return DASHBOARD_HTML

    @app.get("/classic", response_class=HTMLResponse, tags=["kernel"], include_in_schema=False)
    def classic() -> str:
        """Ancienne interface 2D (canvas) — repli/diagnostic."""
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
