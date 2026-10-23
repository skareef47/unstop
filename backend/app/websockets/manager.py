"""
WebSocket Connection and Broadcasting Manager
"""
import asyncio
import json
import logging
from typing import Any, Dict, List, Optional, Set
from fastapi import WebSocket
from app.websockets.events import WSEvent

logger = logging.getLogger("psai.websockets")


class ConnectionManager:
    def __init__(self):
        self._active_connections: Set[WebSocket] = set()
        self._sequence_counter: int = 0
        self._lock = asyncio.Lock()

    async def connect(self, websocket: WebSocket) -> None:
        await websocket.accept()
        self._active_connections.add(websocket)
        logger.info(f"WebSocket client connected. Total clients: {len(self._active_connections)}")

    def disconnect(self, websocket: WebSocket) -> None:
        self._active_connections.discard(websocket)
        logger.info(f"WebSocket client disconnected. Total clients: {len(self._active_connections)}")

    async def broadcast(
        self,
        event_type: str,
        data: Dict[str, Any],
        conversation_id: Optional[str] = None,
    ) -> WSEvent:
        """
        Thread-safe broadcast with monotonic sequence numbering.
        """
        async with self._lock:
            self._sequence_counter += 1
            seq = self._sequence_counter

        event = WSEvent.create(
            event_type=event_type,
            sequence=seq,
            data=data,
            conversation_id=conversation_id,
        )
        payload = event.model_dump_json()

        stale_connections = []
        for connection in list(self._active_connections):
            try:
                await connection.send_text(payload)
            except Exception as e:
                logger.warning(f"Failed to send to client: {e}")
                stale_connections.append(connection)

        for stale in stale_connections:
            self._active_connections.discard(stale)

        return event

    def broadcast_sync(
        self,
        event_type: str,
        data: Dict[str, Any],
        conversation_id: Optional[str] = None,
    ) -> None:
        """Helper to fire-and-forget broadcast from synchronous contexts."""
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                asyncio.create_task(self.broadcast(event_type, data, conversation_id))
            else:
                loop.run_until_complete(self.broadcast(event_type, data, conversation_id))
        except RuntimeError:
            pass


ws_manager = ConnectionManager()
