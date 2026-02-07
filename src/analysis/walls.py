"""Wall thickness analysis.

Checks wall pairs (parallel faces) against minimum thickness rules
for each manufacturing process.
"""

import logging
from src.models.geometry import Wall
from src.models.violations import Violation, ManufacturingProcess
from src.dfm.rules import DFMRule

logger = logging.getLogger(__name__)


class WallAnalyzer:
    """Analyze wall thickness violations."""

    def check(self, walls: list[Wall], rules: list[DFMRule]) -> list[Violation]:
        """Check all walls against wall thickness rules.

        Args:
            walls: Wall pairs from Fusion geometry query.
            rules: Filtered rules for the target process(es).

        Returns:
            List of violations for walls below threshold.
        """
        wall_rules = [r for r in rules if r.category == "wall_thickness"]
        if not wall_rules:
            return []

        violations = []
        for wall in walls:
            for rule in wall_rules:
                if not rule.check(wall.thickness_mm):
                    process = _parse_process(rule.process)
                    violations.append(Violation(
                        rule_id=rule.rule_id,
                        severity=rule.severity,
                        message=rule.format_message(wall.thickness_mm),
                        feature_id=f"wall_{wall.face_index_1}_{wall.face_index_2}",
                        current_value=wall.thickness_mm,
                        required_value=rule.threshold,
                        fixable=rule.fixable,
                        process=process,
                        location=wall.centroid,
                    ))

        return violations


def _parse_process(process_str: str) -> ManufacturingProcess:
    """Convert process string to enum, defaulting to FDM."""
    mapping = {
        "fdm": ManufacturingProcess.FDM,
        "sla": ManufacturingProcess.SLA,
        "cnc": ManufacturingProcess.CNC,
        "injection_molding": ManufacturingProcess.INJECTION_MOLDING,
    }
    return mapping.get(process_str.lower(), ManufacturingProcess.FDM)
