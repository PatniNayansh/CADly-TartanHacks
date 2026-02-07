"""Cadly v2 — FastAPI application entry point."""

import logging
from pathlib import Path

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from src.config import APP_HOST, APP_PORT, LOG_LEVEL, UI_DIR
from src.api.routes import router
from src.api.middleware import setup_middleware
from src.api.websocket import manager

# Logging
logging.basicConfig(
    level=getattr(logging, LOG_LEVEL, logging.INFO),
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)

# App
app = FastAPI(title="Cadly v2", version="2.0.0", description="AI-Powered DFM Analysis for Fusion 360")

# Middleware
setup_middleware(app)

# API routes
app.include_router(router)

# Static files (CSS, JS, components)
app.mount("/static", StaticFiles(directory=str(UI_DIR)), name="static")


# Root — serve UI
@app.get("/")
async def root():
    """Serve the main UI page."""
    return FileResponse(str(UI_DIR / "index.html"))


# WebSocket endpoint
@app.websocket("/ws")
async def websocket_endpoint(ws: WebSocket):
    """WebSocket for real-time status updates."""
    await manager.connect(ws)
    try:
        while True:
            # Keep connection alive, handle incoming messages if needed
            data = await ws.receive_text()
            # Client can send ping/pong
            if data == "ping":
                await ws.send_text("pong")
    except WebSocketDisconnect:
        manager.disconnect(ws)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host=APP_HOST, port=APP_PORT)
