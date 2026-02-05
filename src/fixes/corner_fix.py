"""Cadly Auto-Fix: Corner fillet fix for CNC-001 violations."""

from .base import FixResult, fusion_get, fusion_post, wait_for_fusion
import logging

logger = logging.getLogger(__name__)


def _find_sharp_concave_edges(min_radius_mm: float = 1.5) -> list[int]:
    """Query Fusion and return indices of concave edges with radius < threshold."""
    edges_data = fusion_get("get_edges_info")
    sharp = []
    for edge in edges_data.get("edges", []):
        if not edge.get("is_concave", False):
            continue
        edge_type = edge.get("type", "")
        if edge_type == "line":
            sharp.append(edge["index"])
        elif edge_type in ("arc", "circle"):
            radius_mm = edge.get("radius_cm", 0) * 10
            if radius_mm < min_radius_mm:
                sharp.append(edge["index"])
    return sharp


def apply_corner_fix(feature_id: str, target_radius_mm: float) -> FixResult:
    """
    Fix CNC-001: Add fillet to an internal corner edge.

    Flow: snapshot edges → apply fillet → validate edge count changed.
    If fillet compute fails silently, edge count stays same → report failure (no undo needed).
    """
    rule_id = "CNC-001"
    edge_idx = int(feature_id.split("_")[1])
    radius_cm = target_radius_mm / 10.0

    # Snapshot before
    try:
        edges_before = fusion_get("get_edges_info")
        edge_count_before = len(edges_before.get("edges", []))
    except Exception as e:
        return FixResult(
            success=False, rule_id=rule_id, feature_id=feature_id,
            message=f"Cannot query geometry: {e}",
            old_value=0, new_value=target_radius_mm,
        )

    # Apply fillet (fire-and-forget into Fusion task queue)
    try:
        fusion_post("fillet_specific_edges", {
            "edge_indices": [edge_idx],
            "radius": radius_cm,
        })
        wait_for_fusion(0.8)
    except Exception as e:
        return FixResult(
            success=False, rule_id=rule_id, feature_id=feature_id,
            message=f"Fillet operation failed: {e}",
            old_value=0, new_value=target_radius_mm,
        )

    # Validate: edge count should change
    try:
        edges_after = fusion_get("get_edges_info")
        edge_count_after = len(edges_after.get("edges", []))

        if edge_count_after == edge_count_before:
            return FixResult(
                success=False, rule_id=rule_id, feature_id=feature_id,
                message=f"Fillet could not be applied to edge {edge_idx} (geometry constraint)",
                old_value=0, new_value=target_radius_mm,
            )
    except Exception as e:
        return FixResult(
            success=False, rule_id=rule_id, feature_id=feature_id,
            message=f"Could not validate fix: {e}",
            old_value=0, new_value=target_radius_mm,
        )

    return FixResult(
        success=True, rule_id=rule_id, feature_id=feature_id,
        message=f"Added {target_radius_mm}mm fillet to edge {edge_idx}",
        old_value=0, new_value=target_radius_mm,
    )


def apply_corner_fix_batch(edge_indices: list[int], target_radius_mm: float) -> FixResult:
    """
    Fix multiple CNC-001 edges one at a time.

    After each successful fillet, re-queries geometry for fresh edge indices.
    Within a round, tries each sharp edge; if none succeed, stops.
    """
    rule_id = "CNC-001"
    radius_cm = target_radius_mm / 10.0
    feature_id = f"{len(edge_indices)}_edges"

    succeeded = 0
    total_failed = 0

    for _ in range(20):  # safety cap
        # Fresh query for sharp concave edges
        try:
            sharp_edges = _find_sharp_concave_edges(target_radius_mm)
        except Exception:
            break

        if not sharp_edges:
            break

        # Try each sharp edge in this round until one succeeds
        round_success = False
        for edge_idx in sharp_edges:
            # Snapshot
            try:
                before = fusion_get("get_edges_info")
                count_before = len(before.get("edges", []))
            except Exception:
                continue

            # Fillet
            try:
                fusion_post("fillet_specific_edges", {
                    "edge_indices": [edge_idx],
                    "radius": radius_cm,
                })
                wait_for_fusion(0.8)
            except Exception:
                total_failed += 1
                continue

            # Check
            try:
                after = fusion_get("get_edges_info")
                count_after = len(after.get("edges", []))
            except Exception:
                total_failed += 1
                continue

            if count_after != count_before:
                succeeded += 1
                round_success = True
                break  # Edge indices are now stale — re-query in next round
            else:
                total_failed += 1

        if not round_success:
            break  # No edge in this round could be filleted — stop

    if succeeded == 0:
        return FixResult(
            success=False, rule_id=rule_id, feature_id=feature_id,
            message=f"Could not fillet any edges at {target_radius_mm}mm",
            old_value=0, new_value=target_radius_mm,
        )

    return FixResult(
        success=True, rule_id=rule_id, feature_id=feature_id,
        message=f"Filleted {succeeded} edges at {target_radius_mm}mm ({total_failed} skipped)",
        old_value=0, new_value=target_radius_mm,
    )
