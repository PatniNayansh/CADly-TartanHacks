"""Cost Optimization Specialist Agent."""

import json


def build_prompt(part_data: dict) -> str:
    """Build the cost optimizer review prompt."""
    return f"""You are a manufacturing cost optimization specialist. Review this part for cost efficiency.

PART DATA:
{json.dumps(part_data, indent=2)}

EVALUATE:
1. Process selection — which process gives the best cost/quality ratio?
2. Quantity breakpoints — at what quantity does injection molding become cheaper?
3. Design simplifications — any features that dramatically increase cost but add little value?
4. Material cost — cheaper alternatives that meet requirements?
5. Batch optimization — how to minimize per-unit cost?

RESPOND with ONLY valid JSON:
{{
  "agent": "Cost Optimizer",
  "assessment": "2-4 sentence overall assessment",
  "recommended_process": "the most cost-effective process for prototyping (qty 1-10)",
  "volume_process": "the most cost-effective for production (qty 1000+)",
  "cost_saving_opportunities": [
    {{
      "description": "what to change",
      "estimated_savings_percent": <5-50>,
      "difficulty": "easy/medium/hard"
    }}
  ],
  "quantity_breakpoints": [
    {{
      "quantity": 500,
      "note": "CNC becomes cheaper than SLA above 500 units"
    }}
  ],
  "concerns": ["cost concern 1"],
  "recommendations": ["recommendation 1", "recommendation 2"]
}}

Be specific — reference actual cost estimates and dimensions from the data."""
