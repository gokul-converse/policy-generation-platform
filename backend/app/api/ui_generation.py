import logging
import time
from uuid import uuid4
from app.db.session import get_db

from fastapi import APIRouter, HTTPException, Depends

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.json_policy import UIGenerationRequest
from app.services.ui_generation_pipeline import generate_validated_ui

from app.models.policy_db import PolicyVersion

logger = logging.getLogger(__name__)

ui_generation_router = APIRouter(
    prefix="/api/ui",
    tags=["UI Generation"],
)

async def get_policy_text(
    request: UIGenerationRequest,
    session: AsyncSession,
) -> str:

    # Direct-text testing mode
    if request.policy_text is not None:
        return request.policy_text

    result = await session.execute(
        select(PolicyVersion).where(
            PolicyVersion.policy_id == request.policy_id,
            PolicyVersion.version == request.version,
        )
    )

    version_record = result.scalar_one_or_none()

    if version_record is None:
        raise HTTPException(
            status_code=404,
            detail="Policy version not found.",
        )

    policy_text = version_record.content_text

    if not policy_text or not policy_text.strip():
        raise HTTPException(
            status_code=422,
            detail="Policy content is empty for this version.",
        )

    return policy_text

@ui_generation_router.post("/generate")
async def generate_ui(request: UIGenerationRequest,
                      session: AsyncSession = Depends(get_db),):
    request_id = str(uuid4())
    started_at = time.perf_counter()

    try:
        # Step 1: Retrieve or accept policy text
        policy_text = await get_policy_text(
            request,
            session,
        )

        logger.info(
            "[%s] UI generation request received | policy_chars=%d",
            request_id,
            len(policy_text),
        )

        # Step 2: Existing UI generation pipeline
        ui_definition = await generate_validated_ui(
            policy_text,
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

    except HTTPException:
        raise

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