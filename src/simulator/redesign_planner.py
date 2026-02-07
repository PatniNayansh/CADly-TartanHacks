"""Generate step-by-step redesign roadmaps for process switches."""

import logging
from src.models.violations import Violation, Severity

logger = logging.getLogger(__name__)

# Priority order for redesign steps (lower = do first)
CATEGORY_PRIORITY = {
    "wall_thickness": 1,
    "corner_radius": 2,
    "hole_size": 3,
    "hole_depth": 4,
    "overhang": 5,
    "draft_angle": 5,
    "wall_uniformity": 6,
    "bridge": 7,
    "feature_size": 8,
    "undercut": 9,
    "tool_access": 10,
    "standard_hole": 11,
}

# Human-readable redesign instructions per rule category
REDESIGN_TEMPLATES = {
    "FDM-001": {
        "action": "Increase wall thickness",
        "detail": "Thicken wall from {current:.1f}mm to at least {required:.1f}mm. FDM cannot reliably print thinner walls due to nozzle diameter constraints.",
        "effort": "low",
        "auto_fixable": True,
    },
    "FDM-002": {
        "action": "Reduce overhang angle or add supports",
        "detail": "Face at {current:.0f}\u00b0 overhang exceeds the {required:.0f}\u00b0 FDM limit. Options: redesign to reduce angle, split into multi-part assembly, or accept support material (adds cost + cleanup).",
        "effort": "medium",
        "auto_fixable": False,
    },
    "FDM-003": {
        "action": "Enlarge hole diameter",
        "detail": "Resize hole from {current:.1f}mm to at least {required:.1f}mm. Small holes tend to close up during FDM printing.",
        "effort": "low",
        "auto_fixable": True,
    },
    "FDM-004": {
        "action": "Reduce unsupported bridge span",
        "detail": "Bridge of {current:.1f}mm exceeds the {required:.1f}mm FDM maximum. Add intermediate supports or redesign to break the span.",
        "effort": "medium",
        "auto_fixable": False,
    },
    "SLA-001": {
        "action": "Increase wall thickness",
        "detail": "Thicken wall from {current:.1f}mm to at least {required:.1f}mm for SLA resin strength.",
        "effort": "low",
        "auto_fixable": True,
    },
    "CNC-001": {
        "action": "Add fillet to internal corner",
        "detail": "Add a fillet radius of at least {required:.1f}mm. CNC tools cannot cut perfectly sharp internal corners due to tool geometry.",
        "effort": "low",
        "auto_fixable": True,
    },
    "CNC-002": {
        "action": "Enlarge small feature",
        "detail": "Feature at {current:.1f}mm is below the {required:.1f}mm CNC minimum. Enlarge or remove the feature.",
        "effort": "medium",
        "auto_fixable": False,
    },
    "CNC-003": {
        "action": "Reduce hole depth or increase diameter",
        "detail": "Hole depth-to-diameter ratio of {current:.1f}:1 exceeds {required:.1f}:1 CNC limit. Use a larger drill bit or reduce hole depth.",
        "effort": "medium",
        "auto_fixable": False,
    },
    "CNC-004": {
        "action": "Remove undercut geometry",
        "detail": "Undercut cannot be reached by standard 3-axis CNC tooling. Redesign to eliminate the undercut or plan for multi-axis machining (higher cost).",
        "effort": "high",
        "auto_fixable": False,
    },
    "CNC-005": {
        "action": "Improve tool accessibility",
        "detail": "Depth-to-width ratio of {current:.1f}:1 limits tool access. Widen the feature pocket or reduce depth.",
        "effort": "medium",
        "auto_fixable": False,
    },
    "GEN-001": {
        "action": "Use standard drill size",
        "detail": "Resize hole from {current:.2f}mm to the nearest standard drill size. Reduces cost by using off-the-shelf tooling.",
        "effort": "low",
        "auto_fixable": True,
    },
    "IM-001": {
        "action": "Add draft angle to vertical faces",
        "detail": "Add at least {required:.1f}\u00b0 draft angle for mold release. Without draft, the part will stick in the mold.",
        "effort": "medium",
        "auto_fixable": False,
    },
    "IM-002": {
        "action": "Equalize wall thickness",
        "detail": "Wall thickness variation of {current:.0f}% exceeds the {required:.0f}% IM limit. Uneven walls cause sink marks and warping. Core out thick sections.",
        "effort": "high",
        "auto_fixable": False,
    },
}


class RedesignPlanner:
    """Generate ordered redesign steps from violations."""

    def generate_steps(self, violations: list[Violation], to_process: str) -> list[dict]:
        """Create a prioritized redesign roadmap from violations.

        Args:
            violations: List of violations for the target process.
            to_process: The target manufacturing process.

        Returns:
            List of step dicts, ordered by priority.
        """
        if not violations:
            return []

        steps = []
        for v in violations:
            template = REDESIGN_TEMPLATES.get(v.rule_id)
            if not template:
                # Fallback for unknown rule IDs
                steps.append({
                    "step": 0,
                    "action": f"Address {v.rule_id} violation",
                    "detail": v.message,
                    "effort": "medium",
                    "auto_fixable": v.fixable,
                    "severity": v.severity.value,
                    "rule_id": v.rule_id,
                    "feature_id": v.feature_id,
                    "priority": 50,
                })
                continue

            detail = template["detail"].format(
                current=v.current_value,
                required=v.required_value,
            )

            # Determine category from rule_id
            category = self._rule_category(v.rule_id)
            priority = CATEGORY_PRIORITY.get(category, 50)

            steps.append({
                "step": 0,  # Will be renumbered after sort
                "action": template["action"],
                "detail": detail,
                "effort": template["effort"],
                "auto_fixable": template["auto_fixable"],
                "severity": v.severity.value,
                "rule_id": v.rule_id,
                "feature_id": v.feature_id,
                "priority": priority,
            })

        # Sort: critical first, then by category priority
        severity_order = {"critical": 0, "warning": 1, "suggestion": 2}
        steps.sort(key=lambda s: (severity_order.get(s["severity"], 3), s["priority"]))

        # Renumber steps
        for i, step in enumerate(steps, 1):
            step["step"] = i
            del step["priority"]  # Don't expose internal sort key

        return steps

    @staticmethod
    def _rule_category(rule_id: str) -> str:
        """Map rule_id to its category for priority ordering."""
        category_map = {
            "FDM-001": "wall_thickness",
            "FDM-002": "overhang",
            "FDM-003": "hole_size",
            "FDM-004": "bridge",
            "SLA-001": "wall_thickness",
            "CNC-001": "corner_radius",
            "CNC-002": "feature_size",
            "CNC-003": "hole_depth",
            "CNC-004": "undercut",
            "CNC-005": "tool_access",
            "GEN-001": "standard_hole",
            "IM-001": "draft_angle",
            "IM-002": "wall_uniformity",
        }
        return category_map.get(rule_id, "unknown")
