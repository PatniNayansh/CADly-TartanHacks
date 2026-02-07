"""Hole analysis.

Checks holes for:
- Minimum diameter (FDM can't print very small holes accurately)
- Depth-to-diameter ratio (CNC drill limitations)
- Standard drill size compliance (manufacturing convenience)
"""

import logging
from src.models.geometry import Hole
from src.models.violations import Violation, Severity, ManufacturingProcess
from src.dfm.rules import DFMRule, get_nearest_standard_drill

logger = logging.getLogger(__name__)


class HoleAnalyzer:
    """Analyze hole-related DFM violations."""

    def check(self, holes: list[Hole], rules: list[DFMRule], process: str = "all") -> list[Violation]:
        """Check all holes against relevant rules.

        Args:
            holes: Holes from Fusion geometry query.
            rules: Filtered rules for the target process(es).
            process: Target process for filtering ("all", "fdm", "cnc", etc.)

        Returns:
            List of violations for problematic holes.
        """
        violations = []

        for hole in holes:
            violations.extend(self._check_min_diameter(hole, rules, process))
            violations.extend(self._check_depth_ratio(hole, rules, process))
            violations.extend(self._check_standard_size(hole, rules))

        return violations

    def _check_min_diameter(
        self, hole: Hole, rules: list[DFMRule], process: str,
    ) -> list[Violation]:
        """Check minimum hole diameter rules (FDM-003)."""
        diameter_rules = [r for r in rules if r.category == "hole_size"]
        violations = []

        for rule in diameter_rules:
            if not rule.check(hole.diameter_mm):
                violations.append(Violation(
                    rule_id=rule.rule_id,
                    severity=rule.severity,
                    message=rule.format_message(hole.diameter_mm),
                    feature_id=f"hole_{hole.face_index}",
                    current_value=hole.diameter_mm,
                    required_value=rule.threshold,
                    fixable=rule.fixable,
                    process=ManufacturingProcess.FDM,
                    location=hole.centroid,
                ))

        return violations

    def _check_depth_ratio(
        self, hole: Hole, rules: list[DFMRule], process: str,
    ) -> list[Violation]:
        """Check hole depth-to-diameter ratio rules (CNC-003)."""
        ratio_rules = [r for r in rules if r.category == "hole_depth"]
        violations = []

        if hole.depth_mm <= 0:
            return violations

        for rule in ratio_rules:
            if not rule.check(hole.depth_to_diameter_ratio):
                violations.append(Violation(
                    rule_id=rule.rule_id,
                    severity=rule.severity,
                    message=rule.format_message(hole.depth_to_diameter_ratio),
                    feature_id=f"hole_{hole.face_index}",
                    current_value=hole.depth_to_diameter_ratio,
                    required_value=rule.threshold,
                    fixable=rule.fixable,
                    process=ManufacturingProcess.CNC,
                    location=hole.centroid,
                ))

        return violations

    def _check_standard_size(self, hole: Hole, rules: list[DFMRule]) -> list[Violation]:
        """Check if hole matches a standard drill size (GEN-001)."""
        std_rules = [r for r in rules if r.category == "standard_hole"]
        violations = []

        nearest = get_nearest_standard_drill(hole.diameter_mm)
        deviation = abs(hole.diameter_mm - nearest)

        for rule in std_rules:
            if not rule.check(deviation):
                violations.append(Violation(
                    rule_id=rule.rule_id,
                    severity=rule.severity,
                    message=f"Hole diameter {hole.diameter_mm:.2f}mm is not a standard drill size (nearest: {nearest}mm)",
                    feature_id=f"hole_{hole.face_index}",
                    current_value=hole.diameter_mm,
                    required_value=nearest,
                    fixable=rule.fixable,
                    process=ManufacturingProcess.CNC,
                    location=hole.centroid,
                ))

        return violations
