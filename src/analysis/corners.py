"""Internal corner radius analysis.

Checks concave (internal) edges against minimum corner radius rules.
Sharp internal corners are problematic for CNC because the smallest
end mill determines the minimum achievable radius.
"""

import logging
from src.models.geometry import Edge
from src.models.violations import Violation, ManufacturingProcess
from src.dfm.rules import DFMRule

logger = logging.getLogger(__name__)


class CornerAnalyzer:
    """Analyze internal corner radius violations."""

    def check(self, edges: list[Edge], rules: list[DFMRule]) -> list[Violation]:
        """Check all concave edges against corner radius rules.

        Args:
            edges: Edges from Fusion geometry query.
            rules: Filtered rules for the target process(es).

        Returns:
            List of violations for corners below minimum radius.
        """
        corner_rules = [r for r in rules if r.category == "corner_radius"]
        if not corner_rules:
            return []

        violations = []
        for edge in edges:
            if not edge.is_concave:
                continue

            # Determine radius in mm
            if edge.edge_type == "line":
                radius_mm = 0.0  # Sharp edge, no fillet
            elif edge.edge_type in ("arc", "circle"):
                radius_mm = edge.radius_mm
            else:
                continue

            for rule in corner_rules:
                if not rule.check(radius_mm):
                    violations.append(Violation(
                        rule_id=rule.rule_id,
                        severity=rule.severity,
                        message=rule.format_message(radius_mm),
                        feature_id=f"edge_{edge.index}",
                        current_value=radius_mm,
                        required_value=rule.threshold,
                        fixable=rule.fixable,
                        process=ManufacturingProcess.CNC,
                        location=edge.start,
                    ))

        return violations
