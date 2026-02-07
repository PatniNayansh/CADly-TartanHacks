"""Violation and severity data models for DFM analysis."""

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class Severity(Enum):
    """Violation severity levels."""
    CRITICAL = "critical"
    WARNING = "warning"
    SUGGESTION = "suggestion"


class ManufacturingProcess(Enum):
    """Supported manufacturing processes."""
    FDM = "fdm"
    SLA = "sla"
    CNC = "cnc"
    INJECTION_MOLDING = "injection_molding"


@dataclass
class Violation:
    """A single DFM violation detected in the part geometry."""
    rule_id: str
    severity: Severity
    message: str
    feature_id: str
    current_value: float
    required_value: float
    fixable: bool
    process: ManufacturingProcess
    location: Optional[list[float]] = None
    affected_geometry: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        """Serialize to JSON-compatible dict."""
        return {
            "rule_id": self.rule_id,
            "severity": self.severity.value,
            "message": self.message,
            "feature_id": self.feature_id,
            "current_value": round(self.current_value, 3),
            "required_value": round(self.required_value, 3),
            "fixable": self.fixable,
            "process": self.process.value,
            "location": self.location,
            "affected_geometry": self.affected_geometry,
        }


@dataclass
class ViolationReport:
    """Complete DFM analysis report for a part."""
    part_name: str
    violations: list[Violation]
    is_manufacturable: bool
    recommended_process: Optional[str] = None
    body_volume_cm3: float = 0.0
    body_area_cm2: float = 0.0
    bounding_box: Optional[dict] = None

    @property
    def violation_count(self) -> int:
        return len(self.violations)

    @property
    def critical_count(self) -> int:
        return sum(1 for v in self.violations if v.severity == Severity.CRITICAL)

    @property
    def warning_count(self) -> int:
        return sum(1 for v in self.violations if v.severity == Severity.WARNING)

    @property
    def suggestion_count(self) -> int:
        return sum(1 for v in self.violations if v.severity == Severity.SUGGESTION)

    def to_dict(self) -> dict:
        """Serialize to JSON-compatible dict."""
        return {
            "part_name": self.part_name,
            "violations": [v.to_dict() for v in self.violations],
            "violation_count": self.violation_count,
            "critical_count": self.critical_count,
            "warning_count": self.warning_count,
            "suggestion_count": self.suggestion_count,
            "is_manufacturable": self.is_manufacturable,
            "recommended_process": self.recommended_process,
            "body_volume_cm3": round(self.body_volume_cm3, 4),
            "body_area_cm2": round(self.body_area_cm2, 4),
            "bounding_box": self.bounding_box,
        }
