"""Aplicacao FastAPI do OrbitFire."""

from __future__ import annotations

import logging

from fastapi import FastAPI

from src.api.routes import router
from src.config import Settings, load_settings

logger = logging.getLogger(__name__)


def create_app(settings: Settings | None = None) -> FastAPI:
    """Fabrica da API com Settings injetavel (testes e producao)."""
    app = FastAPI(
        title="OrbitFire API",
        description="Risco preditivo de incendio para o Tocantins (TO)",
        version="0.1.0",
    )
    app.state.settings = settings or load_settings()
    app.include_router(router)
    return app


app = create_app()


def main() -> None:
    """Entrypoint: uvicorn src.api.main:app --reload"""
    import uvicorn

    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    cfg = load_settings()
    uvicorn.run(
        "src.api.main:app",
        host="0.0.0.0",
        port=8000,
        reload=False,
    )
    logger.info("API OrbitFire em http://0.0.0.0:8000 (db=%s)", cfg.db_path)


if __name__ == "__main__":
    main()
