"""FDM 3D Printing Specialist Agent."""

import json


def build_prompt(part_data: dict) -> str:
    """Build the FDM expert review prompt."""
    return f"""You are an FDM 3D printing expert. Review this manufactured part for printability.

PART DATA:
{json.dumps(part_data, indent=2)}

EVALUATE:
1. Printability — can this be printed on a standard FDM printer without supports failing?
2. Orientation — what's the optimal print orientation to minimize supports?
3. Layer adhesion — are there features that would have weak layer bonding?
4. Support requirements — what percentage of the part needs support material?
5. Post-processing — any cleanup, sanding, or assembly needed?

RESPOND with ONLY valid JSON:
{{
  "agent": "FDM Expert",
  "assessment": "2-4 sentence overall assessment",
  "score": <1-10 printability score>,
  "concerns": ["concern 1", "concern 2"],
  "recommendations": ["recommendation 1", "recommendation 2"],
  "optimal_orientation": "description of best print orientation",
  "support_estimate_percent": <0-100>,
  "recommended_settings": {{
    "layer_height_mm": <0.1-0.3>,
    "infill_percent": <10-100>,
    "material": "PLA/PETG/ABS"
  }}
}}

Be specific — reference actual dimensions and feature counts from the data."""
