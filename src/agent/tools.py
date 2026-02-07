"""Tool functions for Dedalus agent - wraps existing Cadly modules."""

from typing import Optional
import asyncio
from src.parsing.cad_parser import parse_mesh
from src.dfm.engine import DFMEngine
from src.costs.estimator import CostEstimator


def parse_cad_file(filepath: str) -> dict:
    """Parse an uploaded CAD file (STL/OBJ) and extract geometry statistics
    including volume, surface area, bounding box, wall thicknesses, holes, and overhangs.

    This tool uses trimesh to load and analyze mesh files. It returns geometry
    data in the same format as get_fusion_geometry() so both paths can feed
    into the same DFM rules engine.

    Args:
        filepath: Path to the STL or OBJ file

    Returns:
        Dictionary with geometry statistics matching GeometryStats schema
    """
    return parse_mesh(filepath)


async def get_fusion_geometry() -> dict:
    """Query the live Fusion 360 design via HTTP to get body properties,
    faces, edges, walls, and holes from the active component.

    This tool connects to the Fusion 360 add-in running on port 5000 and
    extracts the same geometry data that parse_cad_file() returns for uploaded files.

    Returns:
        Dictionary with geometry data matching GeometryStats schema
    """
    # TODO: Implement Fusion HTTP calls once we have the fusion client
    # For now, return mock data
    return {
        "volume_cm3": 30.0,
        "surface_area_cm2": 94.0,
        "bounding_box": {"x": 50.0, "y": 30.0, "z": 20.0},
        "triangle_count": None,
        "vertex_count": None,
        "face_count": 14,
        "body_count": 1,
        "walls": [],
        "holes": [],
    }


def check_dfm_rules(geometry: dict, process: str) -> dict:
    """Run deterministic DFM rule checks against geometry for a manufacturing process.

    This tool applies all DFM rules for the specified process (or all processes if
    process="all") to the geometry data and returns violations grouped by severity.

    Args:
        geometry: Geometry statistics dict from parse_cad_file or get_fusion_geometry
        process: Manufacturing process ("fdm", "sla", "cnc", "injection_molding", "all")

    Returns:
        Dictionary with violations list, blocking_issues, warnings, and is_manufacturable flag
    """
    # TODO: Adapt DFMAnalyzer to accept dict input instead of requiring Fusion client
    # For now, return mock violations
    return {
        "violations": [
            {
                "rule_id": "FDM-001",
                "severity": "critical",
                "message": "Minimum wall thickness 2mm not met",
                "current_value": 1.0,
                "required_value": 2.0,
                "fixable": True,
                "process": "fdm",
                "fix_suggestion": "Increase wall thickness to 2mm via shell feature"
            }
        ],
        "blocking_issues": [],
        "warnings": [],
        "is_manufacturable": False
    }


async def parse_machine_capabilities(machine_description: str) -> list[dict]:
    """Parse a plain-text description of available machines into structured capability records.

    This tool uses a nested Dedalus call with structured output to convert natural
    language machine descriptions into structured data that can be matched against
    part requirements.

    Example input: "I have a Bambu X1C FDM printer and a Tormach PCNC 440 CNC mill"

    Args:
        machine_description: Natural language description of available machines

    Returns:
        List of machine capability dicts with type, build_volume, materials, tolerances
    """
    # TODO: Implement nested Dedalus call for NLP parsing
    # For now, return mock data
    return [
        {
            "name": "Bambu X1C",
            "type": "FDM",
            "build_volume": {"x": 256, "y": 256, "z": 256},
            "materials": ["PLA", "PETG", "ABS", "TPU"],
            "tolerances": "±0.1mm"
        },
        {
            "name": "Tormach PCNC 440",
            "type": "CNC",
            "build_volume": {"x": 254, "y": 140, "z": 254},
            "materials": ["Aluminum", "Steel", "Plastic"],
            "tolerances": "±0.02mm"
        }
    ]


def estimate_manufacturing_cost(
    volume_cm3: float,
    area_cm2: float,
    bounding_box: dict,
    face_count: int,
    process: str,
    quantity: int = 1
) -> dict:
    """Estimate manufacturing cost for a specific process and quantity.

    Uses the existing CostEstimator module to calculate material cost, machine time,
    setup cost, and total cost for the specified manufacturing process.

    Args:
        volume_cm3: Part volume in cubic centimeters
        area_cm2: Surface area in square centimeters
        bounding_box: Bounding box dimensions {x, y, z} in mm
        face_count: Number of faces (complexity indicator)
        process: Manufacturing process ("fdm", "sla", "cnc", "injection_molding")
        quantity: Production quantity

    Returns:
        Cost breakdown dict matching CostBreakdown schema
    """
    estimator = CostEstimator()

    if process == "fdm":
        estimate = estimator.estimate_fdm(volume_cm3, area_cm2, bounding_box)
    elif process == "sla":
        estimate = estimator.estimate_sla(volume_cm3, area_cm2, bounding_box)
    elif process == "cnc":
        estimate = estimator.estimate_cnc(volume_cm3, area_cm2, bounding_box)
    elif process == "injection_molding":
        estimate = estimator.estimate_injection_molding(volume_cm3, area_cm2, bounding_box, quantity)
    else:
        raise ValueError(f"Unknown process: {process}")

    # Convert CostEstimate dataclass to dict
    return estimate.to_dict()


def recommend_machines(process: str, bounding_box: dict, volume_cm3: float) -> list[dict]:
    """Rank machines from database that can manufacture this part.

    Filters machines by process type, checks build volume fit, and ranks by
    suitability score based on size match, capabilities, and cost.

    Args:
        process: Manufacturing process type
        bounding_box: Part bounding box {x, y, z} in mm
        volume_cm3: Part volume

    Returns:
        List of ranked machine recommendations with fit scores
    """
    # TODO: Implement once src/recommend/machine_matcher.py exists
    # For now, return mock recommendations
    return [
        {
            "name": "Bambu X1 Carbon",
            "type": process.upper(),
            "score": 9.2,
            "build_volume_fits": True,
            "reason": "Perfect size match, high precision, fast print speed",
            "limitations": []
        }
    ]


def recommend_materials(process: str) -> list[dict]:
    """Rank materials for a manufacturing process with property scores.

    Queries the material database and scores each material based on strength,
    cost, machinability/printability, and suitability for the given process.

    Args:
        process: Manufacturing process ("fdm", "sla", "cnc", "injection_molding")

    Returns:
        List of materials with spider chart property scores
    """
    # TODO: Implement once src/recommend/material_matcher.py exists
    # For now, return mock recommendations
    if process == "fdm":
        return [
            {
                "name": "PETG",
                "process": "FDM",
                "score": 8.5,
                "properties": {
                    "strength": 7.5,
                    "flexibility": 6.0,
                    "heat_resistance": 6.5,
                    "cost": 8.0,
                    "ease_of_use": 9.0
                },
                "reason": "Good balance of strength, flexibility, and ease of printing"
            }
        ]
    return []


def suggest_fixes(violations: list[dict]) -> list[dict]:
    """Generate fix suggestions for each violation including parametric changes
    and Fusion 360 script stubs.

    Analyzes violations and generates actionable fix suggestions with estimated
    impact and optional Fusion 360 script code for automated fixes.

    Args:
        violations: List of DFM violations from check_dfm_rules

    Returns:
        List of fix suggestions with before/after values and script code
    """
    fixes = []

    for violation in violations:
        rule_id = violation.get("rule_id", "")
        current = violation.get("current_value", 0)
        required = violation.get("required_value", 0)

        if rule_id.startswith("FDM-001") or rule_id.startswith("CNC-001"):
            # Wall thickness fix
            fixes.append({
                "violation_rule_id": rule_id,
                "fix_type": "wall",
                "description": f"Increase wall thickness from {current}mm to {required}mm",
                "estimated_impact": "Resolves critical manufacturability issue",
                "script_stub": None  # Script would be generated by fix runner
            })
        elif "hole" in rule_id.lower():
            # Hole resize fix
            fixes.append({
                "violation_rule_id": rule_id,
                "fix_type": "hole",
                "description": f"Resize hole from {current}mm to {required}mm (nearest standard drill size)",
                "estimated_impact": "Reduces manufacturing cost and improves machinability",
                "script_stub": None
            })
        elif "corner" in rule_id.lower() or "radius" in rule_id.lower():
            # Corner fillet fix
            fixes.append({
                "violation_rule_id": rule_id,
                "fix_type": "corner",
                "description": f"Add {required}mm fillet to sharp internal corners",
                "estimated_impact": "Enables CNC manufacturing, improves tool accessibility",
                "script_stub": None
            })

    return fixes


async def highlight_in_fusion(feature_ids: list[str]) -> dict:
    """Highlight specific faces or features in the live Fusion 360 design
    to show the user where issues are located.

    Sends a command to the Fusion 360 add-in to visually highlight features
    in the 3D viewport with a distinctive color.

    Args:
        feature_ids: List of face/edge IDs to highlight

    Returns:
        Success status dict
    """
    # TODO: Implement HTTP call to Fusion add-in
    # For now, return mock success
    return {
        "success": True,
        "highlighted_count": len(feature_ids),
        "message": f"Highlighted {len(feature_ids)} features in Fusion 360"
    }
