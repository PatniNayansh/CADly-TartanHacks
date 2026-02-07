"""Materials Engineering Specialist Agent."""

import json


def build_prompt(part_data: dict) -> str:
    """Build the materials engineer review prompt."""
    return f"""You are a materials engineer specializing in manufacturing material selection. Review this part.

PART DATA:
{json.dumps(part_data, indent=2)}

EVALUATE:
1. Material suitability — based on the geometry, what materials are best?
2. Strength requirements — are thin walls or small features structurally sound?
3. Thermal properties — any concerns with heat resistance or thermal expansion?
4. Weight optimization — could material changes reduce weight without losing strength?
5. Cost vs performance — where's the sweet spot?

For EACH process (FDM, SLA, CNC), recommend the BEST material.

RESPOND with ONLY valid JSON:
{{
  "agent": "Materials Engineer",
  "assessment": "2-4 sentence overall assessment",
  "material_recommendations": [
    {{
      "process": "FDM",
      "material": "PETG",
      "reason": "why this material for this part",
      "alternatives": ["PLA", "ABS"]
    }},
    {{
      "process": "SLA",
      "material": "Standard Resin",
      "reason": "why",
      "alternatives": ["Tough Resin"]
    }},
    {{
      "process": "CNC",
      "material": "Aluminum 6061-T6",
      "reason": "why",
      "alternatives": ["Brass", "Delrin"]
    }}
  ],
  "concerns": ["concern about specific geometry + material interaction"],
  "recommendations": ["recommendation 1", "recommendation 2"]
}}

Be specific — reference actual part dimensions and geometry features."""
