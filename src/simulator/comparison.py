"""Side-by-side process comparison for the simulator tab."""

import logging

logger = logging.getLogger(__name__)

# Process descriptions shown in comparison UI
PROCESS_INFO = {
    "fdm": {
        "name": "FDM (Fused Deposition Modeling)",
        "short": "FDM",
        "strengths": [
            "Low cost for prototyping",
            "Wide material selection",
            "Large build volumes available",
            "Easy to iterate quickly",
        ],
        "weaknesses": [
            "Visible layer lines",
            "Anisotropic strength (weak between layers)",
            "Requires supports for overhangs > 45\u00b0",
            "Lower dimensional accuracy (\u00b10.2mm)",
        ],
        "best_for": "Prototyping, functional testing, low-volume production",
        "typical_tolerance_mm": 0.2,
        "surface_finish": "Rough (layered)",
    },
    "sla": {
        "name": "SLA (Stereolithography)",
        "short": "SLA",
        "strengths": [
            "Excellent surface finish",
            "High detail resolution",
            "Thin walls down to 1mm",
            "Isotropic material properties",
        ],
        "weaknesses": [
            "Limited material options",
            "UV-sensitive parts (can yellow/become brittle)",
            "Requires post-curing",
            "Smaller build volumes",
        ],
        "best_for": "Detailed prototypes, dental/jewelry, presentation models",
        "typical_tolerance_mm": 0.05,
        "surface_finish": "Smooth",
    },
    "cnc": {
        "name": "CNC Machining",
        "short": "CNC",
        "strengths": [
            "Excellent dimensional accuracy",
            "Real engineering materials (metals, plastics)",
            "Superior surface finish",
            "No layer lines — isotropic",
        ],
        "weaknesses": [
            "Higher cost per part",
            "Internal corners need fillet radius",
            "Limited by tool access (undercuts difficult)",
            "Material waste from subtractive process",
        ],
        "best_for": "Production parts, metal parts, tight-tolerance components",
        "typical_tolerance_mm": 0.025,
        "surface_finish": "Excellent",
    },
    "injection_molding": {
        "name": "Injection Molding",
        "short": "IM",
        "strengths": [
            "Lowest per-unit cost at volume",
            "Extremely fast cycle times",
            "Excellent repeatability",
            "Wide material selection",
        ],
        "weaknesses": [
            "Very high upfront tooling cost ($5k-$50k+)",
            "Requires draft angles on all faces",
            "Wall thickness must be uniform",
            "Long lead time for mold fabrication",
        ],
        "best_for": "High-volume production (1000+ units)",
        "typical_tolerance_mm": 0.05,
        "surface_finish": "Excellent (mold-dependent)",
    },
}


def build_comparison(from_process: str, to_process: str, switch_result: dict) -> dict:
    """Build a side-by-side comparison structure for the UI.

    Args:
        from_process: Source process key (e.g. "fdm").
        to_process: Target process key (e.g. "cnc").
        switch_result: The ProcessSwitchResult.to_dict() output.

    Returns:
        Dict with structured comparison data for the UI.
    """
    from_info = PROCESS_INFO.get(from_process.lower(), PROCESS_INFO["fdm"])
    to_info = PROCESS_INFO.get(to_process.lower(), PROCESS_INFO["fdm"])

    cost_before = switch_result.get("cost_before", {})
    cost_after = switch_result.get("cost_after", {})

    return {
        "from_process": {
            **from_info,
            "cost": cost_before,
            "violation_count": len(switch_result.get("removed_violations", []))
                + len(switch_result.get("persistent_violations", [])),
        },
        "to_process": {
            **to_info,
            "cost": cost_after,
            "violation_count": len(switch_result.get("new_violations", []))
                + len(switch_result.get("persistent_violations", [])),
        },
        "delta": {
            "cost": switch_result.get("cost_delta", 0),
            "violations_resolved": len(switch_result.get("removed_violations", [])),
            "violations_introduced": len(switch_result.get("new_violations", [])),
            "violations_persistent": len(switch_result.get("persistent_violations", [])),
            "tolerance_change": round(
                to_info["typical_tolerance_mm"] - from_info["typical_tolerance_mm"], 3
            ),
        },
        "verdict": _build_verdict(switch_result, from_info, to_info),
    }


def _build_verdict(switch_result: dict, from_info: dict, to_info: dict) -> dict:
    """Generate a quick verdict about the process switch."""
    removed = len(switch_result.get("removed_violations", []))
    new = len(switch_result.get("new_violations", []))
    delta = switch_result.get("cost_delta", 0)

    # Determine if this is an improvement
    score = 0
    reasons = []

    if removed > new:
        score += 1
        reasons.append(f"Resolves {removed - new} more violations than it introduces")
    elif new > removed:
        score -= 1
        reasons.append(f"Introduces {new - removed} more violations than it resolves")

    if delta < -1:
        score += 1
        reasons.append(f"Saves ${abs(delta):.2f} per unit")
    elif delta > 1:
        score -= 1
        reasons.append(f"Costs ${delta:.2f} more per unit")

    if score > 0:
        recommendation = "recommended"
        label = "Switch Recommended"
    elif score < 0:
        recommendation = "not_recommended"
        label = "Switch Not Recommended"
    else:
        recommendation = "neutral"
        label = "Trade-offs are Balanced"

    return {
        "recommendation": recommendation,
        "label": label,
        "reasons": reasons,
    }
