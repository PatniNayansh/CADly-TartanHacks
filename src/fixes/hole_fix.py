"""Hole resize fix for GEN-001 and FDM-003 violations."""

import logging
import textwrap
from src.fusion.client import FusionClient
from src.dfm.rules import get_nearest_standard_drill
from .base import BaseFix, FixResult

logger = logging.getLogger(__name__)


class HoleFix(BaseFix):
    """Resize holes to standard drill sizes or minimum diameters."""

    async def apply(
        self,
        feature_id: str,
        current_diameter_mm: float,
        target_diameter_mm: float | None = None,
        rule_id: str = "GEN-001",
        **kwargs,
    ) -> FixResult:
        """Fix GEN-001/FDM-003: Resize hole via sketch circle manipulation."""
        if target_diameter_mm is None:
            target_diameter_mm = get_nearest_standard_drill(current_diameter_mm)

        if abs(current_diameter_mm - target_diameter_mm) < 0.01:
            return FixResult(True, rule_id, feature_id,
                             "Hole already at target size",
                             current_diameter_mm, target_diameter_mm)

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
            resp = await self.client.execute_script(script)
        except Exception as e:
            return FixResult(False, rule_id, feature_id,
                             f"Script execution failed: {e}",
                             current_diameter_mm, target_diameter_mm)

        if not resp.get("found", False):
            return FixResult(False, rule_id, feature_id,
                             f"No sketch circle found at {current_diameter_mm:.2f}mm. Manual fix needed.",
                             current_diameter_mm, target_diameter_mm)

        # Validate with retry
        async def check():
            holes = await self.client.get("analyze_holes")
            return any(
                abs(h["diameter_mm"] - target_diameter_mm) < 0.2
                for h in holes.get("holes", [])
            )

        if await self.validate_with_retry(check):
            return FixResult(True, rule_id, feature_id,
                             f"Resized hole from {current_diameter_mm:.2f}mm to {target_diameter_mm:.1f}mm",
                             current_diameter_mm, target_diameter_mm)

        # Validation failed — rollback
        await self.rollback()
        return FixResult(False, rule_id, feature_id,
                         "Hole resized but geometry did not update, rolled back",
                         current_diameter_mm, target_diameter_mm, rolled_back=True)
