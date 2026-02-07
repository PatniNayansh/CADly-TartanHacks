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

    target_cm = target_thickness_mm / 10.0

    # Use execute_script to find shell features or cut extrudes and adjust
    script = textwrap.dedent(f"""\
        import adsk.core
        import adsk.fusion

        increase = {increase_cm}
        target_cm = {target_cm}
        fixed = False
        tried = []
        fixed_shells = []

        # First try: Shell features — fix ALL that are under target thickness
        shells = rootComp.features.shellFeatures
        for si in range(shells.count):
            shell = shells.item(si)
            old_val = shell.insideThickness.value  # in cm
            param_name = shell.insideThickness.name if hasattr(shell.insideThickness, 'name') else 'shellThickness'

            # Skip shells already at or above target thickness
            if old_val >= target_cm - 0.001:
                tried.append({{'name': param_name, 'old_cm': round(old_val, 4), 'skipped': True, 'reason': 'already at target'}})
                continue

            tried.append({{'name': param_name, 'old_cm': round(old_val, 4), 'new_cm': round(target_cm, 4), 'type': 'shell'}})
            shell.insideThickness.value = target_cm
            if abs(shell.insideThickness.value - target_cm) < 0.001:
                fixed = True
                fixed_shells.append(param_name)
            else:
                shell.insideThickness.value = old_val

        if fixed_shells:
            result['param_name'] = ', '.join(fixed_shells)
            result['new_depth_cm'] = round(target_cm, 4)

        # Second try: Cut-extrude features (only if no shells were fixed)
        if not fixed:
            extrudes = rootComp.features.extrudeFeatures
            for ei in range(extrudes.count):
                ext = extrudes.item(ei)
                if ext.operation != 1:
                    continue

                extent = ext.extentOne
                if not hasattr(extent, 'distance'):
                    continue

                param = extent.distance
                old_val = param.value
                param_name = param.name if hasattr(param, 'name') else 'unknown'

                if old_val < 0:
                    new_val = old_val + increase
                else:
                    new_val = old_val - increase

                tried.append({{'name': param_name, 'old_cm': round(old_val, 4), 'new_cm': round(new_val, 4), 'type': 'extrude'}})
                param.value = new_val

                if abs(param.value - new_val) > 0.001:
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

    wait_for_fusion(2.0)

    # Validate: check that the thin wall got thicker
    try:
        walls_after = fusion_get("analyze_walls")
        wall_fixed = False
        for w in walls_after.get("walls", []):
            faces = {w["face_index_1"], w["face_index_2"]}
            if face1 in faces or face2 in faces:
                if w["thickness_mm"] >= target_thickness_mm - 0.01:
                    wall_fixed = True
                    break

        if not wall_fixed:
            # Check if ANY thin wall improved (face indices may shift after fix)
            # Only consider actual walls (< 10mm) — skip large distances between
            # opposite sides of the part which aren't real walls.
            real_walls = [
                w["thickness_mm"] for w in walls_after.get("walls", [])
                if w["thickness_mm"] < 10.0
            ]
            min_wall = min(real_walls, default=target_thickness_mm)
            if min_wall >= target_thickness_mm - 0.01:
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
