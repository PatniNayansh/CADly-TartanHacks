"""Async HTTP client for the Fusion 360 add-in running on port 5000.

Replaces the old synchronous requests.get/post calls and the MCP Server
middle layer. All communication with Fusion goes through this client.
"""

import asyncio
import json
import logging
from typing import Any, Optional

import httpx

from src.config import (
    FUSION_BASE_URL,
    FUSION_TIMEOUT,
    FUSION_RETRY_COUNT,
    FUSION_RETRY_DELAY,
    ENDPOINTS,
)

logger = logging.getLogger(__name__)


class FusionError(Exception):
    """Raised when a Fusion 360 operation fails."""
    pass


class FusionConnectionError(FusionError):
    """Raised when unable to connect to the Fusion add-in."""
    pass


class FusionClient:
    """Async HTTP client for the Fusion 360 add-in.

    All Fusion 360 operations go through this client. It handles connection
    pooling, retries with backoff, and error parsing.
    """

    def __init__(self, base_url: str = FUSION_BASE_URL, timeout: float = FUSION_TIMEOUT):
        self.base_url = base_url
        self._client = httpx.AsyncClient(
            base_url=base_url,
            timeout=timeout,
            headers={"Content-Type": "application/json"},
        )

    async def close(self) -> None:
        """Close the HTTP client."""
        await self._client.aclose()

    async def health_check(self) -> bool:
        """Check if the Fusion add-in is reachable."""
        try:
            resp = await self._client.post(ENDPOINTS["test_connection"])
            return resp.status_code == 200
        except (httpx.ConnectError, httpx.TimeoutException):
            return False

    async def get(self, endpoint: str) -> dict:
        """GET request to Fusion add-in with retry logic."""
        url = ENDPOINTS.get(endpoint, endpoint)
        return await self._request("GET", url)

    async def post(self, endpoint: str, data: Optional[dict] = None) -> dict:
        """POST request to Fusion add-in with retry logic."""
        url = ENDPOINTS.get(endpoint, endpoint)
        return await self._request("POST", url, data=data or {})

    async def execute_script(self, code: str, timeout: float = 35) -> dict:
        """Execute Python code inside Fusion 360 via the execute_script endpoint.

        This is used for fixes that need direct access to Fusion's internal API
        (e.g., resizing sketch circles, adjusting extrude depths).
        """
        return await self._request(
            "POST",
            ENDPOINTS["execute_script"],
            data={"code": code},
            timeout=timeout,
        )

    async def undo(self) -> dict:
        """Trigger undo in Fusion 360 and wait briefly for it to process."""
        result = await self.post("undo")
        await asyncio.sleep(0.5)
        return result

    async def _request(
        self,
        method: str,
        url: str,
        data: Optional[dict] = None,
        timeout: Optional[float] = None,
    ) -> dict:
        """Make an HTTP request with retry logic and error handling."""
        last_error: Optional[Exception] = None

        for attempt in range(1, FUSION_RETRY_COUNT + 1):
            try:
                if method == "GET":
                    resp = await self._client.get(url, timeout=timeout)
                else:
                    resp = await self._client.post(
                        url,
                        content=json.dumps(data) if data else None,
                        timeout=timeout,
                    )

                resp.raise_for_status()
                result = resp.json()

                if "error" in result:
                    raise FusionError(result["error"])

                return result

            except httpx.ConnectError as e:
                last_error = FusionConnectionError(
                    f"Cannot connect to Fusion 360 at {self.base_url}. "
                    f"Is the add-in running? Error: {e}"
                )
                if attempt < FUSION_RETRY_COUNT:
                    logger.warning(f"Connection failed (attempt {attempt}/{FUSION_RETRY_COUNT}), retrying...")
                    await asyncio.sleep(FUSION_RETRY_DELAY)

            except httpx.TimeoutException as e:
                last_error = FusionError(f"Request to {url} timed out: {e}")
                if attempt < FUSION_RETRY_COUNT:
                    logger.warning(f"Timeout (attempt {attempt}/{FUSION_RETRY_COUNT}), retrying...")
                    await asyncio.sleep(FUSION_RETRY_DELAY)

            except httpx.HTTPStatusError as e:
                last_error = FusionError(f"HTTP {e.response.status_code} from Fusion: {e}")
                if attempt < FUSION_RETRY_COUNT and e.response.status_code >= 500:
                    logger.warning(f"Server error (attempt {attempt}/{FUSION_RETRY_COUNT}), retrying...")
                    await asyncio.sleep(FUSION_RETRY_DELAY)
                else:
                    break  # Don't retry 4xx errors

            except FusionError:
                raise  # Don't retry Fusion-reported errors

            except Exception as e:
                last_error = FusionError(f"Unexpected error: {e}")
                break

        raise last_error or FusionError("Unknown error")
