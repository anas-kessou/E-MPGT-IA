"""
E-MPGT-IA — FastAPI Main Application
Système IA BTP : Base vectorielle · Intelligence métier · Automatisation

This is the production entry point that initializes all services
and mounts all API routers.
"""

import structlog
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

from app.config import get_settings
from app.routers import chat, documents, knowledge, health, settings as settings_router

# Load environment variables
load_dotenv()

logger = structlog.get_logger()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize all services on startup, cleanup on shutdown."""
    settings = get_settings()
    logger.info("startup_begin", env=settings.app_env)

    # Initialize databases (graceful — skip if service unavailable)
    try:
        from app.database.qdrant import init_collections
        init_collections()
    except Exception as e:
        logger.warning("qdrant_init_skip", error=str(e))

    try:
        from app.database.neo4j_client import init_schema
        init_schema()
    except Exception as e:
        logger.warning("neo4j_init_skip", error=str(e))

    try:
        from app.database.postgres import init_database
        init_database()
    except Exception as e:
        logger.warning("postgres_init_skip", error=str(e))

    try:
        from app.database.minio_client import init_bucket
        init_bucket()
    except Exception as e:
        logger.warning("minio_init_skip", error=str(e))

    logger.info("startup_complete")
    yield
    logger.info("shutdown")


# ── Create FastAPI Application ─────────────────────────────────────

app = FastAPI(
    title="E-MPGT-IA — Système IA BTP",
    description="Base vectorielle · Intelligence métier · Automatisation des opérations",
    version="2.0.0",
    lifespan=lifespan,
)

# ── CORS Middleware ────────────────────────────────────────────────

settings = get_settings()
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Mount Routers ──────────────────────────────────────────────────

app.include_router(chat.router)
app.include_router(documents.router)
app.include_router(knowledge.router)
app.include_router(health.router)
app.include_router(settings_router.router)


# ── Root Endpoint ──────────────────────────────────────────────────

@app.get("/")
async def root():
    return {
        "system": "E-MPGT-IA",
        "description": "Système IA BTP — Base vectorielle · Intelligence métier · Automatisation",
        "version": "2.0.0",
        "endpoints": {
            "chat": "/api/chat",
            "documents": "/api/documents/",
            "knowledge": "/api/knowledge/overview",
            "health": "/api/health",
            "dashboard": "/api/dashboard/stats",
            "settings": "/api/settings/",
        },
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
