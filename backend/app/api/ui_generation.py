import logging
import time
from uuid import uuid4

from fastapi import APIRouter, HTTPException

from app.models.json_policy import UIGenerationRequest
from app.services.ui_generation_pipeline import generate_validated_ui

logger = logging.getLogger(__name__)

ui_generation_router = APIRouter(
    prefix="/api/ui",
    tags=["UI Generation"],
)


@ui_generation_router.post("/generate")
async def generate_ui(request: UIGenerationRequest):
    request_id = str(uuid4())
    started_at = time.perf_counter()

    logger.info(
        "[%s] UI generation request received | policy_chars=%d",
        request_id,
        len(request.policy_text),
    )

    try:
        ui_definition = await generate_validated_ui(
            request.policy_text,
            request_id=request_id,
        )

        duration = time.perf_counter() - started_at

        logger.info(
            "[%s] UI generation completed | duration=%.2fs",
            request_id,
            duration,
        )

        return {
            "request_id": request_id,
            "ui_definition": ui_definition,
        }

    except ValueError as exc:
        logger.warning(
            "[%s] UI generation could not produce valid output: %s",
            request_id,
            str(exc),
        )

        raise HTTPException(
            status_code=502,
            detail={
                "message": "Unable to generate schema-valid UI JSON.",
                "request_id": request_id,
            },
        ) from exc

    except Exception:
        logger.exception(
            "[%s] Unexpected UI generation failure",
            request_id,
        )

        raise HTTPException(
            status_code=500,
            detail={
                "message": "UI generation failed.",
                "request_id": request_id,
            },
        ) from None