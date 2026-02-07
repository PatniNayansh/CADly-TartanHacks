"""AI Design Review Board — orchestrates 4 specialist agents via Dedalus."""

import asyncio
import json
import logging
from typing import Optional

from src.config import DEDALUS_API_KEY, DEDALUS_MODEL
from src.agents.specialists import cnc_expert, fdm_expert, materials_eng, cost_optimizer

logger = logging.getLogger(__name__)

# Lazy import
_dedalus_available = True
try:
    from dedalus_labs import AsyncDedalus, DedalusRunner
except ImportError:
    _dedalus_available = False
    AsyncDedalus = None  # type: ignore
    DedalusRunner = None  # type: ignore


class ReviewBoard:
    """Orchestrates a 4-agent design review via Dedalus Labs."""

    def __init__(self):
        self._client = None
        self._runner = None

    def _ensure_client(self):
        """Lazy-init the Dedalus client."""
        if self._client is not None:
            return
        if not _dedalus_available:
            raise RuntimeError("dedalus_labs package not installed")
        if not DEDALUS_API_KEY:
            raise RuntimeError("DEDALUS_API_KEY not configured")
        self._client = AsyncDedalus()
        self._runner = DedalusRunner(self._client)

    async def run_review(self, part_data: dict) -> dict:
        """Run the full 4-agent review. Returns structured report dict."""
        self._ensure_client()

        # Run all 4 specialists in parallel
        prompts = {
            "CNC Expert": cnc_expert.build_prompt(part_data),
            "FDM Expert": fdm_expert.build_prompt(part_data),
            "Materials Engineer": materials_eng.build_prompt(part_data),
            "Cost Optimizer": cost_optimizer.build_prompt(part_data),
        }

        results = await asyncio.gather(
            *[self._run_agent(name, prompt) for name, prompt in prompts.items()],
            return_exceptions=True,
        )

        # Collect successful results
        agent_outputs = {}
        for (name, _), result in zip(prompts.items(), results):
            if isinstance(result, Exception):
                logger.error(f"Agent {name} failed: {result}")
                agent_outputs[name] = {"agent": name, "assessment": f"Agent failed: {result}", "error": True}
            else:
                agent_outputs[name] = result

        # Run synthesizer
        synthesis = await self._synthesize(agent_outputs, part_data)

        return {
            "agents": agent_outputs,
            "synthesis": synthesis,
        }

    async def _run_agent(self, name: str, prompt: str) -> dict:
        """Run a single specialist agent and parse its JSON response."""
        response = await self._runner.run(input=prompt, model=DEDALUS_MODEL)
        raw = response.final_output
        cleaned = _strip_json_fences(raw)
        try:
            return json.loads(cleaned)
        except json.JSONDecodeError:
            return {"agent": name, "assessment": raw, "parse_error": True}

    async def _synthesize(self, agent_outputs: dict, part_data: dict) -> dict:
        """Run the synthesis agent to combine all specialist opinions."""
        prompt = f"""You are the Design Review Board Chair. Synthesize these 4 specialist assessments into a final recommendation.

SPECIALIST ASSESSMENTS:
{json.dumps(agent_outputs, indent=2)}

ORIGINAL PART DATA:
{json.dumps(part_data, indent=2)}

Create a unified recommendation that:
1. Identifies the BEST manufacturing process for this part
2. Highlights the top 3 most important findings across all specialists
3. Lists specific action items ordered by priority
4. Provides a final manufacturability score (1-10)

RESPOND with ONLY valid JSON:
{{
  "recommended_process": "FDM/SLA/CNC",
  "confidence": "high/medium/low",
  "manufacturability_score": <1-10>,
  "executive_summary": "3-5 sentence summary for a busy engineer",
  "top_findings": [
    {{
      "finding": "description",
      "severity": "critical/warning/info",
      "source_agent": "agent name"
    }}
  ],
  "action_items": [
    {{
      "priority": 1,
      "action": "what to do",
      "reason": "why"
    }}
  ],
  "process_comparison": {{
    "fdm_score": <1-10>,
    "sla_score": <1-10>,
    "cnc_score": <1-10>,
    "best_for_prototype": "process name",
    "best_for_production": "process name"
  }}
}}"""

        try:
            response = await self._runner.run(input=prompt, model=DEDALUS_MODEL)
            cleaned = _strip_json_fences(response.final_output)
            return json.loads(cleaned)
        except Exception as e:
            logger.error(f"Synthesis failed: {e}")
            return {
                "executive_summary": "Synthesis failed. Review individual agent assessments above.",
                "error": str(e),
            }


def _strip_json_fences(text: str) -> str:
    """Remove markdown code fences from LLM output."""
    text = text.strip()
    if text.startswith("```json"):
        text = text[7:]
    elif text.startswith("```"):
        text = text[3:]
    if text.endswith("```"):
        text = text[:-3]
    return text.strip()
