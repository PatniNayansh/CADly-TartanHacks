"""Cadly Auto-Fix: Hole resize via direct sketch circle manipulation."""

from .base import FixResult, fusion_get, fusion_exec, fusion_undo, wait_for_fusion
from src.dfm.rules import get_nearest_standard_drill
import logging
import textwrap

logger = logging.getLogger(__name__)


def apply_hole_fix(
    feature_id: str,
    current_diameter_mm: float,
    target_diameter_mm: float | None = None,
    rule_id: str = "GEN-001",
) -> FixResult:
    """
    Fix GEN-001 or FDM-003: Resize hole to standard/minimum diameter.

    Uses execute_script to find sketch circles by radius and resize directly.
    """
    if target_diameter_mm is None:
        target_diameter_mm = get_nearest_standard_drill(current_diameter_mm)

    if abs(current_diameter_mm - target_diameter_mm) < 0.01:
        return FixResult(
            success=True, rule_id=rule_id, feature_id=feature_id,
            message="Hole already at target size",
            old_value=current_diameter_mm, new_value=target_diameter_mm,
        )

    current_radius_cm = current_diameter_mm / 20.0
    target_radius_cm = target_diameter_mm / 20.0

    script = textwrap.dedent(f"""\
        found = False
        for si in range(rootComp.sketches.count):
            sketch = rootComp.sketches.item(si)
            circles = sketch.sketchCurves.sketchCircles
            for ci in range(circles.count):
                c = circles.item(ci)
                if abs(c.radius - {current_radius_cm}) < 0.005:
                    c.radius = {target_radius_cm}
                    found = True
                    break
            if found:
                break
        result['found'] = found
    """)

    try:
        resp = fusion_exec(script)
    except Exception as e:
        return FixResult(
            success=False, rule_id=rule_id, feature_id=feature_id,
            message=f"Script execution failed: {e}",
            old_value=current_diameter_mm, new_value=target_diameter_mm,
        )

    if not resp.get('found', False):
        return FixResult(
            success=False, rule_id=rule_id, feature_id=feature_id,
            message=(
                f"No sketch circle found with radius {current_radius_cm:.4f}cm "
                f"({current_diameter_mm:.2f}mm dia). Manual fix: change hole to {target_diameter_mm:.1f}mm."
            ),
            old_value=current_diameter_mm, new_value=target_diameter_mm,
        )

    wait_for_fusion(1.5)

    # Validate
    try:
        holes_after = fusion_get("analyze_holes")
        found_updated = False
        for hole in holes_after.get("holes", []):
            if abs(hole["diameter_mm"] - target_diameter_mm) < 0.2:
                found_updated = True
                break

        if not found_updated:
            fusion_undo()
            return FixResult(
                success=False, rule_id=rule_id, feature_id=feature_id,
                message="Circle resized but hole geometry did not update, rolled back",
                old_value=current_diameter_mm, new_value=target_diameter_mm,
                rolled_back=True,
            )
    except Exception as e:
        fusion_undo()
        return FixResult(
            success=False, rule_id=rule_id, feature_id=feature_id,
            message=f"Validation failed: {e}, rolled back",
            old_value=current_diameter_mm, new_value=target_diameter_mm,
            rolled_back=True,
        )

    return FixResult(
        success=True, rule_id=rule_id, feature_id=feature_id,
        message=f"Resized hole from {current_diameter_mm:.2f}mm to {target_diameter_mm:.1f}mm",
        old_value=current_diameter_mm, new_value=target_diameter_mm,
    )
