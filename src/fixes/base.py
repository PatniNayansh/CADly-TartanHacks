"""Base fix class and FixResult dataclass."""

import asyncio
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass

from src.fusion.client import FusionClient
from src.config import FIX_VALIDATION_RETRIES, FIX_VALIDATION_DELAY

logger = logging.getLogger(__name__)


@dataclass
class FixResult:
    """Result of a single fix attempt."""
    success: bool
    rule_id: str
    feature_id: str
    message: str
    old_value: float
    new_value: float
    rolled_back: bool = False

    def to_dict(self) -> dict:
        return {
            "success": self.success,
            "rule_id": self.rule_id,
            "feature_id": self.feature_id,
            "message": self.message,
            "old_value": round(self.old_value, 3),
            "new_value": round(self.new_value, 3),
            "rolled_back": self.rolled_back,
        }


class BaseFix(ABC):
    """Abstract base class for DFM fixes."""

    def __init__(self, client: FusionClient):
        self.client = client

    @abstractmethod
    async def apply(self, **kwargs) -> FixResult:
        """Apply the fix. Subclasses must implement."""
        ...

    async def validate_with_retry(self, check_fn, retries: int = FIX_VALIDATION_RETRIES) -> bool:
        """Poll Fusion to validate a fix succeeded, with retries."""
        for attempt in range(retries):
            await asyncio.sleep(FIX_VALIDATION_DELAY)
            try:
                if await check_fn():
                    return True
            except Exception as e:
                logger.warning(f"Validation attempt {attempt + 1} failed: {e}")
        return False

    async def rollback(self) -> None:
        """Undo the last Fusion operation."""
        try:
            await self.client.undo()
        except Exception as e:
            logger.error(f"Rollback failed: {e}")
