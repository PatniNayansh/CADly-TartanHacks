"""Fix orchestrator — applies fixes in optimal order with deduplication."""

import logging
from src.fusion.client import FusionClient
from src.models.violations import Violation
from src.api.websocket import manager
from .base import FixResult
from .hole_fix import HoleFix
from .wall_fix import WallFix
from .corner_fix import CornerFix

logger = logging.getLogger(__name__)


class FixRunner:
    """Orchestrates multiple DFM fixes in the correct order.

    Order: holes -> walls -> corners (fillets change edge indices last).
    """

    def __init__(self, client: FusionClient):
        self.client = client
        self.hole_fix = HoleFix(client)
        self.wall_fix = WallFix(client)
        self.corner_fix = CornerFix(client)

    async def fix_single(self, violation: dict) -> FixResult:
        """Apply a fix for a single violation dict."""
        rule_id = violation.get("rule_id", "")
        feature_id = violation.get("feature_id", "")
        current_value = violation.get("current_value", 0)
        target_value = violation.get("target_value") or violation.get("required_value", 0)

        if rule_id == "CNC-001":
            return await self.corner_fix.apply(
                feature_id=feature_id,
                target_radius_mm=target_value or 1.5,
            )
        elif rule_id in ("GEN-001", "FDM-003"):
            return await self.hole_fix.apply(
                feature_id=feature_id,
                current_diameter_mm=current_value,
                target_diameter_mm=target_value,
                rule_id=rule_id,
            )
        elif rule_id in ("FDM-001", "SLA-001"):
            return await self.wall_fix.apply(
                feature_id=feature_id,
                current_thickness_mm=current_value,
                target_thickness_mm=target_value or 2.0,
                rule_id=rule_id,
            )
        else:
            return FixResult(False, rule_id, feature_id,
                             f"No auto-fix available for {rule_id}", 0, 0)

    async def fix_all(self, violations: list[Violation]) -> list[FixResult]:
        """Apply all fixable violations in optimal order."""
        fixable = [v for v in violations if v.fixable]
        if not fixable:
            return []

        # Group and deduplicate
        hole_fixes: dict[str, Violation] = {}
        wall_fixes: dict[str, Violation] = {}
        corner_edges: list[int] = []
        corner_radius = 1.5

        for v in fixable:
            if v.rule_id in ("GEN-001", "FDM-003"):
                key = v.feature_id
                if key not in hole_fixes or v.required_value > hole_fixes[key].required_value:
                    hole_fixes[key] = v
            elif v.rule_id in ("FDM-001", "SLA-001"):
                key = v.feature_id
                if key not in wall_fixes or v.required_value > wall_fixes[key].required_value:
                    wall_fixes[key] = v
            elif v.rule_id == "CNC-001":
                if v.current_value > 0:
                    continue  # Already has a radius
                try:
                    edge_idx = int(v.feature_id.split("_")[1])
                    corner_edges.append(edge_idx)
                except (IndexError, ValueError):
                    pass
                corner_radius = max(corner_radius, v.required_value)

        results: list[FixResult] = []
        total = len(hole_fixes) + len(wall_fixes) + (1 if corner_edges else 0)
        done = 0

        # Phase 1: Holes (parameter changes, stable topology)
        for fid, v in hole_fixes.items():
            await manager.send_status(f"Fixing hole {fid}...", done / max(total, 1))
            result = await self.hole_fix.apply(
                feature_id=fid,
                current_diameter_mm=v.current_value,
                target_diameter_mm=v.required_value,
                rule_id=v.rule_id,
            )
            results.append(result)
            done += 1

        # Phase 2: Walls (parameter changes, may shift faces)
        for fid, v in wall_fixes.items():
            await manager.send_status(f"Fixing wall {fid}...", done / max(total, 1))
            result = await self.wall_fix.apply(
                feature_id=fid,
                current_thickness_mm=v.current_value,
                target_thickness_mm=v.required_value,
                rule_id=v.rule_id,
            )
            results.append(result)
            done += 1

        # Phase 3: Corners last (fillets change edge indices)
        if corner_edges:
            await manager.send_status("Fixing corners...", done / max(total, 1))
            result = await self.corner_fix.apply_batch(
                edge_indices=corner_edges,
                target_radius_mm=corner_radius,
            )
            results.append(result)

        await manager.send_status("Fixes complete!", 1.0)
        return results
