"""WebSocket handler for real-time progress updates."""

import asyncio
import json
import logging
from typing import Optional

from fastapi import WebSocket, WebSocketDisconnect

logger = logging.getLogger(__name__)


class ConnectionManager:
    """Manages active WebSocket connections and broadcasts messages."""

    def __init__(self):
        self.active: list[WebSocket] = []

    async def connect(self, ws: WebSocket) -> None:
        """Accept and register a WebSocket connection."""
        await ws.accept()
        self.active.append(ws)
        logger.info(f"WebSocket connected. Total: {len(self.active)}")

    def disconnect(self, ws: WebSocket) -> None:
        """Remove a disconnected WebSocket."""
        if ws in self.active:
            self.active.remove(ws)
        logger.info(f"WebSocket disconnected. Total: {len(self.active)}")

    async def broadcast(self, message: dict) -> None:
        """Send a JSON message to all connected clients."""
        dead = []
        for ws in self.active:
            try:
                await ws.send_json(message)
            except Exception:
                dead.append(ws)
        for ws in dead:
            self.disconnect(ws)

    async def send_status(self, step: str, progress: Optional[float] = None) -> None:
        """Broadcast a status update."""
        msg = {"type": "status", "step": step}
        if progress is not None:
            msg["progress"] = round(progress, 2)
        await self.broadcast(msg)

    async def send_result(self, event: str, data: dict) -> None:
        """Broadcast a result event."""
        await self.broadcast({"type": event, "data": data})


# Singleton manager
manager = ConnectionManager()
