"""CNC Machining Specialist Agent."""

import json


def build_prompt(part_data: dict) -> str:
    """Build the CNC expert review prompt."""
    return f"""You are a CNC machining expert with 20 years of experience. Review this manufactured part.

PART DATA:
{json.dumps(part_data, indent=2)}

EVALUATE:
1. Machinability — can standard 3-axis CNC produce this? Would 5-axis be needed?
2. Tool access — are there internal features a tool can't reach?
3. Fixturing — how would this part be held? Multiple setups needed?
4. Tolerances — are the feature sizes achievable with standard tooling?
5. Surface finish — any concerns with surface quality?

RESPOND with ONLY valid JSON:
{{
  "agent": "CNC Expert",
  "assessment": "2-4 sentence overall assessment",
  "score": <1-10 machinability score>,
  "concerns": ["concern 1", "concern 2"],
  "recommendations": ["recommendation 1", "recommendation 2"],
  "tool_requirements": "standard 3-axis / 5-axis / mill-turn",
  "estimated_setups": <number>,
  "critical_issues": ["any showstoppers"]
}}

Be specific — reference actual dimensions and feature counts from the data."""
