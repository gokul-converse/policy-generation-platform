
"""WebSocket endpoint for requirement gathering conversations."""

import logging

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from pydantic import ValidationError

from app.schemas.requirements import RequirementInput
from app.services.requirement_workflow_service import (
    process_requirement_message,
)

logger = logging.getLogger(__name__)

router = APIRouter()


@router.websocket("/ws/requirements")
async def requirement_websocket(websocket: WebSocket):
    await websocket.accept()
    logger.info("Requirement WebSocket connection accepted.")

    try:
        while True:
            try:
                payload = await websocket.receive_json()
                logger.info("Received requirement event: %s", payload.get("event"))

                request = RequirementInput.model_validate(payload)

                result = await process_requirement_message(request)

                logger.info(
                    "Requirement workflow completed. Event: %s",
                    result.get("event"),
                )

                await websocket.send_json(result)

            except ValidationError as exc:
                logger.warning("Invalid WebSocket request: %s", exc)

                await websocket.send_json(
                    {
                        "event": "error",
                        "message": "Invalid request payload.",
                        "details": exc.errors(
                            include_input=False,
                            include_url=False,
                        ),
                    }
                )

            except ValueError as exc:
                logger.warning(
                    "Requirement workflow validation error: %s",
                    exc,
                    exc_info=True,
                )

                await websocket.send_json(
                    {
                        "event": "error",
                        "message": str(exc),
                    }
                )

            except Exception:
                logger.exception(
                    "Unexpected error in requirement WebSocket workflow."
                )

                await websocket.send_json(
                    {
                        "event": "error",
                        "message": (
                            "An internal error occurred while processing "
                            "the requirement. Check the backend logs."
                        ),
                    }
                )

    except WebSocketDisconnect:
        logger.info("Requirement WebSocket client disconnected.")
