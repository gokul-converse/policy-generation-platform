"""FastAPI application entry point."""

from fastapi import FastAPI

from app.api.policies import router as policies_router
from app.api.skills import router as skills_router
from app.common.logger import setup_logging

app = FastAPI(
    title="Policy Generation API",
    description="API for generating and managing reusable policy skills and enterprise policies.",
    version="0.1.0",
)
setup_logging()


@app.get("/health")
async def health_check():
    """Return the application's health status."""
    return {"status": "healthy"}


app.include_router(skills_router)
app.include_router(policies_router)
