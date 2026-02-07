"""CORS, error handling, and logging middleware."""

import logging
import time
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware

logger = logging.getLogger(__name__)


def setup_middleware(app: FastAPI) -> None:
    """Configure all middleware for the FastAPI app."""

    # CORS — allow everything for hackathon
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.middleware("http")
    async def log_requests(request: Request, call_next):
        """Log request method, path, and timing."""
        start = time.time()
        response = await call_next(request)
        elapsed = (time.time() - start) * 1000
        logger.info(f"{request.method} {request.url.path} -> {response.status_code} ({elapsed:.0f}ms)")
        return response


def error_response(code: str, message: str, status: int = 500) -> JSONResponse:
    """Standard error response format."""
    return JSONResponse(
        status_code=status,
        content={
            "success": False,
            "data": None,
            "error": {"code": code, "message": message},
        },
    )


def success_response(data: dict) -> dict:
    """Standard success response format."""
    return {"success": True, "data": data, "error": None}
