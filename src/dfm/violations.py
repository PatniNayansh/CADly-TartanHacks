from dataclasses import dataclass, field, asdict
from enum import Enum
from typing import Optional


class Severity(Enum):
    CRITICAL = "critical"
    WARNING = "warning"
    SUGGESTION = "suggestion"


class ManufacturingProcess(Enum):
    FDM = "fdm"
    SLA = "sla"
    CNC = "cnc"


@dataclass
class Violation:
    rule_id: str
    severity: Severity
    message: str
    feature_id: str
    current_value: float
    required_value: float
    fixable: bool
    location: Optional[list] = None

    def to_dict(self) -> dict:
        return {
            "rule_id": self.rule_id,
            "severity": self.severity.value,
            "message": self.message,
            "feature_id": self.feature_id,
            "current_value": self.current_value,
            "required_value": self.required_value,
            "fixable": self.fixable,
            "location": self.location,
        }


@dataclass
class DFMResult:
    part_name: str
    violations: list[Violation] = field(default_factory=list)
    is_manufacturable: bool = True
    recommended_process: Optional[str] = None
    body_volume_cm3: float = 0.0
    body_area_cm2: float = 0.0

    def to_dict(self) -> dict:
        return {
            "part_name": self.part_name,
            "violations": [v.to_dict() for v in self.violations],
            "violation_count": len(self.violations),
            "critical_count": sum(1 for v in self.violations if v.severity == Severity.CRITICAL),
            "warning_count": sum(1 for v in self.violations if v.severity == Severity.WARNING),
            "is_manufacturable": self.is_manufacturable,
            "recommended_process": self.recommended_process,
            "body_volume_cm3": self.body_volume_cm3,
            "body_area_cm2": self.body_area_cm2,
        }
