"""DFM rule definitions and checking utilities."""

import json
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from src.config import DATA_DIR
from src.models.violations import Severity, ManufacturingProcess

logger = logging.getLogger(__name__)


@dataclass
class DFMRule:
    """A single DFM rule definition."""
    rule_id: str
    name: str
    process: str  # "fdm", "sla", "cnc", "injection_molding", "all"
    severity: Severity
    threshold: float
    unit: str
    comparison: str  # "min" or "max"
    message_template: str
    fixable: bool
    category: str
    priority: int

    def check(self, value: float) -> bool:
        """Check if a value passes this rule. Returns True if OK, False if violation."""
        if self.comparison == "min":
            return value >= self.threshold
        elif self.comparison == "max":
            return value <= self.threshold
        return True

    def format_message(self, value: float, **kwargs) -> str:
        """Format the violation message with actual values."""
        return self.message_template.format(
            value=value,
            threshold=self.threshold,
            **kwargs,
        )

    def applies_to_process(self, process: str) -> bool:
        """Check if this rule applies to a given manufacturing process."""
        if self.process == "all":
            return True
        return self.process == process.lower()

    @classmethod
    def from_dict(cls, data: dict) -> "DFMRule":
        """Parse from JSON dict."""
        severity_map = {
            "critical": Severity.CRITICAL,
            "warning": Severity.WARNING,
            "suggestion": Severity.SUGGESTION,
        }
        return cls(
            rule_id=data["id"],
            name=data["name"],
            process=data["process"],
            severity=severity_map[data["severity"]],
            threshold=data["threshold"],
            unit=data["unit"],
            comparison=data["comparison"],
            message_template=data["message_template"],
            fixable=data["fixable"],
            category=data["category"],
            priority=data.get("priority", 1),
        )


# --- Standard drill sizes ---

_standard_holes_cache: Optional[list[float]] = None


def _load_standard_holes() -> list[float]:
    """Load standard drill sizes from JSON."""
    global _standard_holes_cache
    if _standard_holes_cache is not None:
        return _standard_holes_cache

    path = DATA_DIR / "standard_holes.json"
    try:
        with open(path, "r") as f:
            data = json.load(f)
        _standard_holes_cache = sorted(data["metric_mm"])
    except Exception as e:
        logger.warning(f"Could not load standard holes from {path}: {e}")
        _standard_holes_cache = [
            1.0, 1.5, 2.0, 2.5, 3.0, 3.5, 4.0, 4.5, 5.0, 5.5,
            6.0, 6.5, 7.0, 7.5, 8.0, 8.5, 9.0, 9.5, 10.0,
            10.5, 11.0, 11.5, 12.0, 13.0, 14.0, 15.0, 16.0,
            17.0, 18.0, 19.0, 20.0, 21.0, 22.0, 24.0, 25.0,
        ]
    return _standard_holes_cache


def get_nearest_standard_drill(diameter_mm: float) -> float:
    """Find the nearest standard drill size to the given diameter."""
    sizes = _load_standard_holes()
    if not sizes:
        return diameter_mm
    return min(sizes, key=lambda s: abs(s - diameter_mm))


def get_standard_drill_sizes() -> list[float]:
    """Return the list of standard metric drill sizes in mm."""
    return list(_load_standard_holes())
