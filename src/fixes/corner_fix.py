"""Corner fillet fix for CNC-001 violations."""

import logging
from src.fusion.client import FusionClient
from .base import BaseFix, FixResult

logger = logging.getLogger(__name__)


class CornerFix(BaseFix):
    """Add fillets to sharp internal corners."""

    async def _safe_radius_cm(self, target_radius_mm: float) -> float:
        """Cap fillet radius to half the thinnest wall so fillets don't destroy geometry."""
        try:
            faces_data = await self.client.get("get_faces_info")
            faces = faces_data.get("faces", [])
            planar = [f for f in faces if f.get("type") == "plane" and f.get("normal")]

            min_wall_mm = 999.0
            for i, f1 in enumerate(planar):
                n1 = f1["normal"]
                for j in range(i + 1, len(planar)):
                    f2 = planar[j]
                    n2 = f2["normal"]
                    dot = n1[0]*n2[0] + n1[1]*n2[1] + n1[2]*n2[2]
                    if abs(dot - 1.0) > 0.05:
                        continue
                    c1 = f1.get("centroid", [0, 0, 0])
                    c2 = f2.get("centroid", [0, 0, 0])
                    dx, dy, dz = c1[0]-c2[0], c1[1]-c2[1], c1[2]-c2[2]
                    dist_mm = abs(n2[0]*dx + n2[1]*dy + n2[2]*dz) * 10
                    if 0.01 < dist_mm < min_wall_mm:
                        min_wall_mm = dist_mm

            if min_wall_mm < 999.0:
                safe_mm = min(target_radius_mm, min_wall_mm * 0.4)
                logger.info(f"Min wall {min_wall_mm:.1f}mm, capping fillet to {safe_mm:.2f}mm")
            else:
                safe_mm = target_radius_mm
        except Exception:
            safe_mm = min(target_radius_mm, 0.5)

        return max(safe_mm, 0.1) / 10.0  # convert to cm, minimum 0.1mm

    async def apply(
        self,
        feature_id: str,
        target_radius_mm: float = 1.5,
        **kwargs,
    ) -> FixResult:
        """Fix CNC-001: Add fillet to a sharp internal corner edge."""
        rule_id = "CNC-001"
        edge_idx = int(feature_id.split("_")[1])
        radius_cm = await self._safe_radius_cm(target_radius_mm)
        actual_radius_mm = radius_cm * 10

        # Snapshot before
        try:
            edges_before = await self.client.get("get_edges_info")
            count_before = len(edges_before.get("edges", []))
        except Exception as e:
            return FixResult(False, rule_id, feature_id,
                             f"Cannot query geometry: {e}", 0, target_radius_mm)

        # Apply fillet
        try:
            await self.client.post("fillet_specific_edges", {
                "edge_indices": [edge_idx],
                "radius": radius_cm,
            })
        except Exception as e:
            return FixResult(False, rule_id, feature_id,
                             f"Fillet operation failed: {e}", 0, target_radius_mm)

        # Validate: check for new arc edges at the applied radius
        async def check():
            edges_after = await self.client.get("get_edges_info")
            new_arcs = [
                e for e in edges_after.get("edges", [])
                if e.get("type") in ("arc", "circle")
                and abs((e.get("radius_cm", 0) * 10) - actual_radius_mm) < 0.5
            ]
            return len(new_arcs) > 0

        if await self.validate_with_retry(check):
            msg = f"Added {actual_radius_mm:.1f}mm fillet to edge {edge_idx}"
            if actual_radius_mm < target_radius_mm:
                msg += f" (capped from {target_radius_mm:.1f}mm to protect thin walls)"
            return FixResult(True, rule_id, feature_id, msg, 0, actual_radius_mm)

        return FixResult(False, rule_id, feature_id,
                         f"Fillet could not be applied to edge {edge_idx}",
                         0, target_radius_mm)

    async def apply_batch(
        self,
        edge_indices: list[int],
        target_radius_mm: float = 1.5,
    ) -> FixResult:
        """Fix multiple sharp corners one at a time, re-querying after each."""
        rule_id = "CNC-001"
        radius_cm = await self._safe_radius_cm(target_radius_mm)
        actual_radius_mm = radius_cm * 10
        feature_id = f"{len(edge_indices)}_edges"
        succeeded = 0

        for _ in range(20):  # safety cap
            # Find current sharp concave edges
            try:
                edges_data = await self.client.get("get_edges_info")
                sharp = [
                    e["index"] for e in edges_data.get("edges", [])
                    if e.get("is_concave") and (
                        e.get("type") == "line"
                        or (e.get("radius_cm", 0) * 10 < actual_radius_mm)
                    )
                ]
            except Exception:
                break

            if not sharp:
                break

            round_success = False
            for eidx in sharp:
                try:
                    before = await self.client.get("get_edges_info")
                    count_before = len(before.get("edges", []))
                except Exception:
                    continue

                try:
                    await self.client.post("fillet_specific_edges", {
                        "edge_indices": [eidx],
                        "radius": radius_cm,
                    })
                except Exception:
                    continue

                async def check(cb=count_before, r=actual_radius_mm):
                    after = await self.client.get("get_edges_info")
                    new_arcs = [
                        e for e in after.get("edges", [])
                        if e.get("type") in ("arc", "circle")
                        and abs((e.get("radius_cm", 0) * 10) - r) < 0.5
                    ]
                    return len(new_arcs) > 0

                if await self.validate_with_retry(check, retries=2):
                    succeeded += 1
                    round_success = True
                    break  # Re-query in next round (indices are stale)

            if not round_success:
                break

        if succeeded == 0:
            return FixResult(False, rule_id, feature_id,
                             f"Could not fillet any edges at {actual_radius_mm:.1f}mm",
                             0, actual_radius_mm)

        msg = f"Filleted {succeeded} edges at {actual_radius_mm:.1f}mm"
        if actual_radius_mm < target_radius_mm:
            msg += f" (capped from {target_radius_mm:.1f}mm to protect thin walls)"
        return FixResult(True, rule_id, feature_id, msg, 0, actual_radius_mm)
