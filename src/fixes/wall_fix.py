"""Wall thickness fix for FDM-001 and SLA-001 violations."""

import logging
import textwrap
from src.fusion.client import FusionClient
from .base import BaseFix, FixResult

logger = logging.getLogger(__name__)


class WallFix(BaseFix):
    """Increase thin wall thickness by adjusting cut-extrude depth or shell thickness."""

    async def apply(
        self,
        feature_id: str,
        current_thickness_mm: float,
        target_thickness_mm: float,
        rule_id: str = "FDM-001",
        **kwargs,
    ) -> FixResult:
        """Fix FDM-001/SLA-001: Reduce pocket depth or increase shell thickness."""
        increase_mm = target_thickness_mm - current_thickness_mm
        if increase_mm <= 0:
            return FixResult(True, rule_id, feature_id,
                             "Wall already at target thickness",
                             current_thickness_mm, target_thickness_mm)

        increase_cm = increase_mm / 10.0
        target_cm = target_thickness_mm / 10.0

        script = textwrap.dedent(f"""\
            import adsk.core
            import adsk.fusion

            increase = {increase_cm}
            target_cm = {target_cm}
            fixed = False
            tried = []

            # Strategy 1: Adjust cut-extrude depth
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

                tried.append({{'name': param_name, 'old_cm': round(old_val, 4), 'new_cm': round(new_val, 4)}})
                param.value = new_val

                if abs(param.value - new_val) > 0.001:
                    param.value = old_val
                    continue

                fixed = True
                result['param_name'] = param_name
                result['old_depth_cm'] = round(old_val, 4)
                result['new_depth_cm'] = round(new_val, 4)
                break

            # Strategy 2: Adjust shell thickness (for shelled parts)
            if not fixed:
                shells = rootComp.features.shellFeatures
                for si in range(shells.count):
                    shell = shells.item(si)
                    try:
                        old_val = shell.insideThickness.value
                        shell.insideThickness.value = target_cm
                        if abs(shell.insideThickness.value - target_cm) < 0.001:
                            fixed = True
                            result['param_name'] = 'shellThickness'
                            result['old_depth_cm'] = round(old_val, 4)
                            result['new_depth_cm'] = round(target_cm, 4)
                            break
                        else:
                            shell.insideThickness.value = old_val
                    except:
                        pass

            result['fixed'] = fixed
            result['tried'] = tried
        """)

        try:
            resp = await self.client.execute_script(script)
        except Exception as e:
            return FixResult(False, rule_id, feature_id,
                             f"Script execution failed: {e}",
                             current_thickness_mm, target_thickness_mm)

        if not resp.get("fixed", False):
            return FixResult(False, rule_id, feature_id,
                             f"Cannot auto-fix wall ({current_thickness_mm:.1f}mm -> {target_thickness_mm:.1f}mm). "
                             f"No adjustable cut-extrude or shell feature found.",
                             current_thickness_mm, target_thickness_mm)

        # Validate with retry
        face_parts = feature_id.replace("wall_", "").split("_")
        target = target_thickness_mm

        async def check():
            walls = await self.client.get("analyze_walls")
            for w in walls.get("walls", []):
                if w["thickness_mm"] >= target - 0.2:
                    return True
            return False

        if await self.validate_with_retry(check):
            param_name = resp.get("param_name", "?")
            return FixResult(True, rule_id, feature_id,
                             f"Increased wall from {current_thickness_mm:.1f}mm to "
                             f"{target_thickness_mm:.1f}mm (via {param_name})",
                             current_thickness_mm, target_thickness_mm)

        # Validation failed — rollback
        await self.rollback()
        return FixResult(False, rule_id, feature_id,
                         "Wall depth adjusted but thickness did not improve, rolled back",
                         current_thickness_mm, target_thickness_mm, rolled_back=True)
