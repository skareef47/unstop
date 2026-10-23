"""
WebSocket Real-time Dashboard Events Route
"""
import logging
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query
from app.websockets.manager import ws_manager

logger = logging.getLogger("psai.ws_api")
router = APIRouter(tags=["WebSockets"])


@router.websocket("/ws/dashboard")
async def websocket_dashboard_endpoint(
    websocket: WebSocket,
    token: str = Query(None),
):
    """
    Subscribes dashboard clients to authorized live event updates:
    - message.created
    - case.updated
    - classification.completed
    - diagnostic.step_completed
    - action_plan.generated
    - action.completed
    - ticket.created
    """
    await ws_manager.connect(websocket)
    try:
        while True:
            # Keep connection alive; handle incoming heartbeats
            data = await websocket.receive_text()
            if data == "ping":
                await websocket.send_text("pong")
    except WebSocketDisconnect:
        ws_manager.disconnect(websocket)
    except Exception as e:
        logger.warning(f"WebSocket client error: {e}")
        ws_manager.disconnect(websocket)
