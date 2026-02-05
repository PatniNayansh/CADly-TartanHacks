from dataclasses import dataclass
from .violations import Severity, ManufacturingProcess


@dataclass
class DFMRule:
    rule_id: str
    name: str
    process: ManufacturingProcess
    severity: Severity
    threshold: float
    unit: str
    comparison: str  # "min" = value must be >= threshold, "max" = value must be <= threshold
    message_template: str
    fixable: bool


# All DFM rules organized by manufacturing process
RULES: list[DFMRule] = [
    # FDM 3D Printing rules
    DFMRule(
        "FDM-001", "Min Wall Thickness (FDM)",
        ManufacturingProcess.FDM, Severity.CRITICAL,
        2.0, "mm", "min",
        "Wall thickness {value:.1f}mm is below {threshold}mm minimum for FDM printing",
        True,
    ),
    DFMRule(
        "FDM-002", "Max Overhang Angle",
        ManufacturingProcess.FDM, Severity.WARNING,
        45.0, "deg", "max",
        "Overhang angle {value:.0f}° exceeds {threshold}° max for FDM (needs supports)",
        False,
    ),
    DFMRule(
        "FDM-003", "Min Hole Diameter (FDM)",
        ManufacturingProcess.FDM, Severity.WARNING,
        3.0, "mm", "min",
        "Hole diameter {value:.1f}mm is below {threshold}mm minimum for FDM",
        True,
    ),

    # SLA 3D Printing rules
    DFMRule(
        "SLA-001", "Min Wall Thickness (SLA)",
        ManufacturingProcess.SLA, Severity.CRITICAL,
        1.0, "mm", "min",
        "Wall thickness {value:.1f}mm is below {threshold}mm minimum for SLA printing",
        True,
    ),

    # CNC Machining rules
    DFMRule(
        "CNC-001", "Min Internal Corner Radius",
        ManufacturingProcess.CNC, Severity.CRITICAL,
        1.5, "mm", "min",
        "Internal corner radius {value:.1f}mm is below {threshold}mm minimum for CNC",
        True,
    ),
    DFMRule(
        "CNC-002", "Max Hole Depth-to-Diameter Ratio",
        ManufacturingProcess.CNC, Severity.WARNING,
        4.0, "ratio", "max",
        "Hole depth:diameter ratio {value:.1f} exceeds {threshold} max (drill may break)",
        False,
    ),

    # General rules (apply to all processes)
    DFMRule(
        "GEN-001", "Non-Standard Hole Size",
        ManufacturingProcess.CNC, Severity.SUGGESTION,
        0.1, "mm", "max",
        "Hole diameter {value:.2f}mm is not a standard drill size (nearest: {threshold}mm)",
        True,
    ),
]


# Standard metric drill bit sizes in mm
STANDARD_DRILL_SIZES_MM: list[float] = [
    1.0, 1.5, 2.0, 2.5, 3.0, 3.5, 4.0, 4.5, 5.0, 5.5,
    6.0, 6.5, 7.0, 7.5, 8.0, 8.5, 9.0, 9.5, 10.0,
    10.5, 11.0, 11.5, 12.0, 13.0, 14.0, 15.0, 16.0,
    17.0, 18.0, 19.0, 20.0, 21.0, 22.0, 24.0, 25.0,
]


def get_nearest_standard_drill(diameter_mm: float) -> float:
    """Find the nearest standard drill size for a given diameter."""
    return min(STANDARD_DRILL_SIZES_MM, key=lambda d: abs(d - diameter_mm))


def get_rules_for_process(process: ManufacturingProcess) -> list[DFMRule]:
    """Get all rules applicable to a specific manufacturing process."""
    return [r for r in RULES if r.process == process]


def check_rule(rule: DFMRule, value: float) -> bool:
    """Check if a value passes a rule. Returns True if it passes (no violation)."""
    if rule.comparison == "min":
        return value >= rule.threshold
    elif rule.comparison == "max":
        return value <= rule.threshold
    return True
