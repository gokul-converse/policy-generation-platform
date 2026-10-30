"""FastAPI application entry point."""

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.policies import router as policies_router
from app.api.skills import router as skills_router
from app.api.ui_generation import ui_generation_router
from app.api.websocket import router as requirement_websocket_router
from app.common.logger import setup_logging
from app.db.session import dispose_db_engine, initialize_fts

setup_logging()
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(application: FastAPI) -> AsyncIterator[None]:
    """Initialize database search support and clean up on shutdown."""
    try:
        await initialize_fts()
        logger.info("FTS5 initialization completed.")
        yield
    except Exception:
        logger.exception("Application startup or runtime lifecycle failed.")
        raise
    finally:
        await dispose_db_engine()
        logger.info("Database engine disposed.")


app = FastAPI(
    title="Policy Generation API",
    description=(
        "API for generating and managing reusable policy skills "
        "and enterprise policies."
    ),
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
async def health_check():
    """Return the application's basic health status."""
    return {"status": "healthy"}


app.include_router(skills_router)
app.include_router(policies_router)
app.include_router(requirement_websocket_router)
app.include_router(ui_generation_router)
