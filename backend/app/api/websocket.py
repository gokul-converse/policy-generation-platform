
"""WebSocket endpoint for requirement gathering conversations."""

import asyncio
import json
import logging
import time

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from pydantic import ValidationError

from app.schemas.requirements import RequirementInput
from app.services.requirement_workflow_service import (
    process_requirement_message,
)

logger = logging.getLogger(__name__)

router = APIRouter()

WORKFLOW_TIMEOUT = 180


@router.websocket("/ws/requirements")
async def requirement_websocket(websocket: WebSocket):
    await websocket.accept()

    logger.info("Requirement WebSocket connection accepted.")

    try:
        while True:
            session_id = None
            event = None

            try:
                try:
                    payload = await websocket.receive_json()
                except (json.JSONDecodeError, ValueError) as exc:
                    logger.warning("Invalid JSON received on WebSocket: %s", exc)
                    await websocket.send_json(
                        {
                            "event": "error",
                            "message": "Invalid JSON payload received.",
                        }
                    )
                    continue

                event = payload.get("event")
                session_id = payload.get("session_id")

                logger.info(
                    "Received event=%s session_id=%s",
                    event,
                    session_id,
                )

                # Application-level heartbeat
                if event == "ping":
                    await websocket.send_json({"event": "pong"})
                    continue

                request = RequirementInput.model_validate(payload)

                start_time = time.monotonic()

                try:
                    result = await asyncio.wait_for(
                        process_requirement_message(request),
                        timeout=WORKFLOW_TIMEOUT,
                    )

                except asyncio.TimeoutError:
                    logger.error(
                        "Requirement workflow timed out. "
                        "Event=%s session_id=%s timeout=%s",
                        event,
                        session_id,
                        WORKFLOW_TIMEOUT,
                    )

                    await websocket.send_json(
                        {
                            "event": "error",
                            "message": (
                                "Requirement processing timed out. "
                                "Please retry using the same session."
                            ),
                            "session_id": session_id,
                        }
                    )
                    continue

                duration = time.monotonic() - start_time

                logger.info(
                    "Workflow completed. Event=%s session_id=%s "
                    "duration=%.2fs result_event=%s",
                    event,
                    session_id,
                    duration,
                    result.get("event"),
                )

                await websocket.send_json(result)

            except WebSocketDisconnect:
                raise

            except ValidationError as exc:
                logger.warning(
                    "Invalid WebSocket request: %s",
                    exc,
                )

                await websocket.send_json(
                    {
                        "event": "error",
                        "message": "Invalid request payload.",
                        "session_id": session_id,
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
                        "session_id": session_id,
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
                        "session_id": session_id,
                    }
                )

    except WebSocketDisconnect:
        logger.info("Requirement WebSocket client disconnected.")

    except Exception:
        logger.exception("Requirement WebSocket connection failed.")
