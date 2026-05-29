"""FastAPI application factory."""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.api.routes import (
    dsm_agents,
    dsm_documents,
    dsm_graph,
    dsm_graph_agents,
    dsm_rag,
    dsm_registry,
    dsm_search,
    dsm_versions,
    health,
    ingestion,
)
from app.core.config import get_settings
from app.core.logging import RequestIdMiddleware, configure_logging


def create_app() -> FastAPI:
    configure_logging()
    settings = get_settings()
    app = FastAPI(title=settings.app_name, debug=settings.debug, version="0.1.0")
    app.add_middleware(RequestIdMiddleware)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(health.router)
    app.include_router(dsm_versions.router)
    app.include_router(dsm_documents.router)
    app.include_router(dsm_registry.router)
    app.include_router(dsm_search.router)
    app.include_router(dsm_agents.router)
    app.include_router(dsm_rag.router)
    app.include_router(dsm_graph.router)
    app.include_router(dsm_graph_agents.router)
    app.include_router(ingestion.router)
    app.mount("/static", StaticFiles(directory="static"), name="static")
    return app


app = create_app()
