
"""FastAPI application entry point."""

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.policies import router as policies_router
from app.api.skills import router as skills_router
from app.api.websocket import router as requirement_websocket_router
from app.common.logger import setup_logging
from app.db.session import dispose_db_engine, initialize_fts
from fastapi import FastAPI
from pydantic import BaseModel, Field
from fastapi import HTTPException
from app.agents.foundry.agent import get_ui_json_agent

from fastapi.middleware.cors import CORSMiddleware
from app.validators.ui_json_validator import validate_ui_definition
from app.services.ui_generation_pipeline import generate_validated_ui
from app.models.json_policy import UIGenerationRequest
from app.core.logging_config import configure_logging

import json
import logging
from uuid import uuid4
import time
from uuid import uuid4
import time

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


@app.get("/health")
async def health_check():
    """Return the application's basic health status."""
    return {"status": "healthy"}


app.include_router(skills_router)
app.include_router(policies_router)
app.include_router(requirement_websocket_router)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

configure_logging()
logger = logging.getLogger(__name__)

@app.post("/api/ui/generate")
async def generate_ui(request: UIGenerationRequest):

    request_id = str(uuid4())
    started_at = time.perf_counter()

    logger.info(
        "[%s] Request received | endpoint=/api/ui/generate | policy_chars=%d",
        request_id,
        len(request.policy_text),
    )

    try:
        ui_definition = await generate_validated_ui(request.policy_text, request_id=request_id)

        duration = time.perf_counter() - started_at

        logger.info(
            "[%s] Request completed | status=200 | duration=%.2fs",
            request_id,
            duration,
        )

        return {"request_id": request_id, "ui_definition": ui_definition}

    except ValueError as exc:
        duration = time.perf_counter() - started_at

        logger.error(
            "[%s] Generation pipeline could not produce valid output "
            "| status=502 | duration=%.2fs | reason=%s",
            request_id,
            duration,
            str(exc),
        )

        raise HTTPException(
            status_code=502,
            detail={
                "message": "Unable to generate schema-valid UI JSON.",
                "request_id": request_id,
            },
        ) from exc

    except HTTPException:
        raise

    except Exception as exc:
        duration = time.perf_counter() - started_at
        # Keep internal details in server logs, not the public response.
        logger.exception(
            "[%s] Unexpected API failure | duration=%.2fs",
            request_id,
            duration,
        )

        raise HTTPException(
            status_code=500,
            detail={
                "message": "UI generation failed.",
                "request_id": request_id,
            },
        )

    
# @app.post("/api/ui/generate")
# async def generate_ui(request: UIGenerationRequest):
#     try:
#         agent = get_ui_json_agent()

#         response = await agent.run(request.policy_text)

#         # The agent should return a JSON string.(JSON syntax parsing)
#         ui_definition = json.loads(response.text)

#         if not isinstance(ui_definition, dict):
#             raise HTTPException(
#                 status_code=502,
#                 detail="The agent response must be a JSON object.",
#             )

#         # Step 2: Validate automatically in memory.
#         validation_errors = validate_ui_definition(ui_definition)

#         # Step 3: Never send schema-invalid JSON to the frontend.
#         if validation_errors:
#             raise HTTPException(
#                 status_code=502,
#                 detail={
#                     "message": "Generated UI failed schema validation.",
#                     "errors": validation_errors,
#                 },
#             )
        
#         # Step 4: Return only validated JSON.
#         return {"ui_definition": ui_definition}

#     except json.JSONDecodeError as exc:
#         raise HTTPException(
#             status_code=502,
#             detail="The Foundry agent returned invalid JSON.",
#         ) from exc

#     except HTTPException:
#         raise

#     except Exception as exc:
#         raise HTTPException(
#             status_code=500,
#             detail="UI generation failed.",
#         ) from exc
