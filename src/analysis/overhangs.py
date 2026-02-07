"""Overhang angle analysis for FDM printing.

Checks face normals to detect downward-facing surfaces that exceed
the maximum overhang angle. These require support material in FDM.

Overhang angle calculation:
- Face normal Z component determines angle from vertical
- Only downward-facing faces (negative Z normal) are checked
- angle_from_down = acos(-nz), overhang_angle = 90 - angle_from_down
- Overhang angle > 45 degrees = likely needs support
"""

import math
import logging
from src.models.geometry import Face
from src.models.violations import Violation, ManufacturingProcess
from src.dfm.rules import DFMRule

logger = logging.getLogger(__name__)


class OverhangAnalyzer:
    """Analyze overhang angle violations for FDM printing."""

    def check(self, faces: list[Face], rules: list[DFMRule]) -> list[Violation]:
        """Check downward-facing surfaces against overhang angle rules.

        Args:
            faces: Faces from Fusion geometry query.
            rules: Filtered rules for the target process(es).

        Returns:
            List of violations for faces exceeding max overhang angle.
        """
        overhang_rules = [r for r in rules if r.category == "overhang"]
        if not overhang_rules:
            return []

        violations = []
        for face in faces:
            if face.face_type != "plane":
                continue
            if face.normal is None:
                continue

            nz = face.normal[2]

            # Only check downward-facing surfaces (negative Z normal)
            if nz >= 0:
                continue

            # Calculate overhang angle
            angle_from_down = math.degrees(math.acos(max(-1.0, min(1.0, -nz))))
            overhang_angle = 90.0 - angle_from_down

            if overhang_angle < 0:
                continue

            for rule in overhang_rules:
                if not rule.check(overhang_angle):
                    violations.append(Violation(
                        rule_id=rule.rule_id,
                        severity=rule.severity,
                        message=rule.format_message(overhang_angle),
                        feature_id=f"face_{face.index}",
                        current_value=overhang_angle,
                        required_value=rule.threshold,
                        fixable=rule.fixable,
                        process=ManufacturingProcess.FDM,
                        location=face.centroid,
                    ))

        return violations
