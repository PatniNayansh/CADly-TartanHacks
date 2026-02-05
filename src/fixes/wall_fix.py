"""Cadly Auto-Fix: Wall thickness fix via extrude depth adjustment."""

from .base import FixResult, fusion_get, fusion_exec, fusion_undo, wait_for_fusion
import logging
import textwrap

logger = logging.getLogger(__name__)


def apply_wall_fix(
    feature_id: str,
    current_thickness_mm: float,
    target_thickness_mm: float,
    rule_id: str = "FDM-001",
) -> FixResult:
    """
    Fix FDM-001/SLA-001: Increase wall thickness.

    Strategy: Find cut-extrude features and try reducing their depth.
    After each attempt, validate wall thickness improved.
    Falls back to manual guidance if no extrude adjustment works.
    """
    increase_mm = target_thickness_mm - current_thickness_mm
    if increase_mm <= 0:
        return FixResult(
            success=True, rule_id=rule_id, feature_id=feature_id,
            message="Wall already at target thickness",
            old_value=current_thickness_mm, new_value=target_thickness_mm,
        )

    increase_cm = increase_mm / 10.0

    # Get face indices from feature_id (e.g. "wall_5_11")
    face_parts = feature_id.replace("wall_", "").split("_")
    face1, face2 = int(face_parts[0]), int(face_parts[1])

    # Use execute_script to find cut extrudes and try adjusting each one
    script = textwrap.dedent(f"""\
        import adsk.core
        import adsk.fusion

        increase = {increase_cm}
        fixed = False
        tried = []

        # Get cut extrude features
        extrudes = rootComp.features.extrudeFeatures
        for ei in range(extrudes.count):
            ext = extrudes.item(ei)
            # Only look at cut operations (operation == 1)
            if ext.operation != 1:
                continue

            extent = ext.extentOne
            if not hasattr(extent, 'distance'):
                continue

            param = extent.distance
            old_val = param.value  # in cm, negative for cuts
            param_name = param.name if hasattr(param, 'name') else 'unknown'

            # For negative cuts: reduce magnitude (make less deep)
            # For positive cuts: also reduce magnitude
            if old_val < 0:
                new_val = old_val + increase
            else:
                new_val = old_val - increase

            tried.append({{'name': param_name, 'old_cm': round(old_val, 4), 'new_cm': round(new_val, 4)}})
            param.value = new_val

            # Check if it actually changed
            if abs(param.value - new_val) > 0.001:
                # Fusion rejected the change
                param.value = old_val
                continue

            fixed = True
            result['param_name'] = param_name
            result['old_depth_cm'] = round(old_val, 4)
            result['new_depth_cm'] = round(new_val, 4)
            break

        result['fixed'] = fixed
        result['tried'] = tried
    """)

    try:
        resp = fusion_exec(script)
    except Exception as e:
        return FixResult(
            success=False, rule_id=rule_id, feature_id=feature_id,
            message=f"Script execution failed: {e}",
            old_value=current_thickness_mm, new_value=target_thickness_mm,
        )

    if not resp.get('fixed', False):
        return FixResult(
            success=False, rule_id=rule_id, feature_id=feature_id,
            message=(
                f"Cannot auto-fix wall thickness ({current_thickness_mm:.1f}mm -> "
                f"{target_thickness_mm:.1f}mm). Manual fix: Edit the pocket sketch "
                f"and increase the offset from the outer edge by "
                f"{increase_mm:.1f}mm on each side."
            ),
            old_value=current_thickness_mm, new_value=target_thickness_mm,
        )

    wait_for_fusion(1.5)

    # Validate: check that the thin wall got thicker
    try:
        walls_after = fusion_get("analyze_walls")
        wall_fixed = False
        for w in walls_after.get("walls", []):
            faces = {w["face_index_1"], w["face_index_2"]}
            if face1 in faces or face2 in faces:
                if w["thickness_mm"] >= target_thickness_mm - 0.2:
                    wall_fixed = True
                    break

        if not wall_fixed:
            # Check if ANY thin wall improved (face indices may shift)
            min_wall = min(
                (w["thickness_mm"] for w in walls_after.get("walls", [])),
                default=0,
            )
            if min_wall >= target_thickness_mm - 0.2:
                wall_fixed = True

        if not wall_fixed:
            fusion_undo()
            return FixResult(
                success=False, rule_id=rule_id, feature_id=feature_id,
                message=(
                    f"Adjusted extrude depth but wall thickness did not improve "
                    f"sufficiently, rolled back. Manual fix: reduce pocket depth by "
                    f"{increase_mm:.1f}mm."
                ),
                old_value=current_thickness_mm, new_value=target_thickness_mm,
                rolled_back=True,
            )
    except Exception as e:
        fusion_undo()
        return FixResult(
            success=False, rule_id=rule_id, feature_id=feature_id,
            message=f"Validation failed: {e}, rolled back",
            old_value=current_thickness_mm, new_value=target_thickness_mm,
            rolled_back=True,
        )

    param_name = resp.get('param_name', '?')
    return FixResult(
        success=True, rule_id=rule_id, feature_id=feature_id,
        message=(
            f"Increased wall from {current_thickness_mm:.1f}mm to "
            f"{target_thickness_mm:.1f}mm (reduced pocket depth via {param_name})"
        ),
        old_value=current_thickness_mm, new_value=target_thickness_mm,
    )
