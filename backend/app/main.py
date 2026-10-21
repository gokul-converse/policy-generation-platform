
"""FastAPI application entry point."""

from app.api.skills import router as skills_router
from app.common.logger import setup_logging
from fastapi import FastAPI



# Keep your existing FastAPI initialization below.

app = FastAPI(
    title="Policy Generation API",
    description="API for generating and managing reusable policy skills.",
    version="0.1.0",
)
setup_logging()

@app.get("/health")
async def health_check():
    """Return the application's health status."""
    return {"status": "healthy"}


app.include_router(skills_router)
