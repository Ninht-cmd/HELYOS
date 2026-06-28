"""Permet ``python -m jarvis_kernel`` pour démarrer l'API."""

from __future__ import annotations


def main() -> None:
    try:
        import uvicorn
    except ImportError:  # pragma: no cover
        raise SystemExit(
            "uvicorn n'est pas installé. Installez la couche serveur :\n"
            '    pip install -e ".[server]"'
        )

    from .config import settings

    uvicorn.run(
        "jarvis_kernel.main:app",
        host=settings.host,
        port=settings.port,
        reload=False,
    )


if __name__ == "__main__":
    main()
