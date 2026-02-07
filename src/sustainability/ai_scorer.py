"""Dedalus Labs AI agent swarm for sustainability scoring."""

import asyncio
import json
import logging
from typing import Optional

from dedalus_labs import AsyncDedalus, DedalusRunner

from src.config import DEDALUS_MODEL
from src.models.sustainability import (
    WasteEstimate,
    CarbonEstimate,
    AIProcessAnalysis,
    AITradeOff,
    AISustainabilityReport,
)

logger = logging.getLogger(__name__)


class AISustainabilityScorer:
    """Orchestrates a 3-agent Dedalus swarm for sustainability analysis."""

    def __init__(self):
        self._client: Optional[AsyncDedalus] = None
        self._runner: Optional[DedalusRunner] = None

    def _ensure_client(self):
        """Lazy-init the Dedalus client."""
        if self._client is None:
            self._client = AsyncDedalus()
            self._runner = DedalusRunner(self._client)

    async def score(
        self,
        waste_estimates: list[WasteEstimate],
        carbon_estimates: list[CarbonEstimate],
        part_info: dict,
    ) -> AISustainabilityReport:
        """Run the full 3-agent swarm. Raises on failure."""
        self._ensure_client()

        waste_data = [w.to_dict() for w in waste_estimates]
        carbon_data = [c.to_dict() for c in carbon_estimates]

        # Agents 1 & 2 run in PARALLEL
        env_result, energy_result = await asyncio.gather(
            self._run_environmental_analyst(waste_data, part_info),
            self._run_energy_expert(carbon_data, part_info),
        )

        # Agent 3: Synthesizer uses both results
        synthesis = await self._run_synthesizer(
            waste_data, carbon_data, env_result, energy_result, part_info
        )

        return self._parse_synthesis(synthesis, env_result, energy_result)

    async def _run_environmental_analyst(
        self, waste_data: list[dict], part_info: dict
    ) -> str:
        """Agent 1: Environmental Impact Analyst."""
        prompt = f"""You are an Environmental Impact Analyst specializing in manufacturing sustainability.

TASK: Analyze the material waste data for this manufactured part and provide per-process environmental assessments.

PART INFORMATION:
- Volume: {part_info.get('volume_cm3', 'unknown')} cm³
- Bounding box: {json.dumps(part_info.get('bounding_box', {}))}
- Materials: PLA (FDM), Photopolymer Resin (SLA), Aluminum 6061 (CNC), ABS (Injection Molding)

WASTE DATA PER PROCESS:
{json.dumps(waste_data, indent=2)}

ANALYZE each process for:
1. Material efficiency (waste percentage in context — is this typical for the process?)
2. Recyclability and real-world recycling infrastructure availability
3. End-of-life impact (landfill persistence, ocean pollution risk, decomposition timeline)
4. Circular economy potential (can waste chips/supports/failed prints be reused?)
5. A contextual comparison that makes the waste tangible for non-experts (e.g., "69g of aluminum waste = weight of 3 soda cans")

RESPOND with ONLY valid JSON in this exact format:
{{
  "analyses": [
    {{
      "process": "FDM",
      "waste_sub_score": <0-40 integer, higher=less waste=better>,
      "recyclability_sub_score": <0-20 integer>,
      "strengths": ["strength 1", "strength 2"],
      "weaknesses": ["weakness 1"],
      "circular_economy_notes": "one sentence on reuse potential",
      "contextual_comparison": "relatable comparison",
      "reasoning": "2-3 sentences explaining scores with specific numbers"
    }},
    {{ "process": "SLA", ... }},
    {{ "process": "CNC", ... }},
    {{ "process": "Injection Molding", ... }}
  ]
}}

Be specific and quantitative — reference actual gram/percentage values from the data."""

        response = await self._runner.run(input=prompt, model=DEDALUS_MODEL)
        return response.final_output

    async def _run_energy_expert(
        self, carbon_data: list[dict], part_info: dict
    ) -> str:
        """Agent 2: Energy & Emissions Expert."""
        prompt = f"""You are an Energy & Emissions Expert specializing in manufacturing carbon footprints.

TASK: Analyze the energy consumption and CO₂ emissions for this manufactured part across 4 processes.

PART INFORMATION:
- Volume: {part_info.get('volume_cm3', 'unknown')} cm³

ENERGY & CARBON DATA PER PROCESS:
{json.dumps(carbon_data, indent=2)}

CONTEXT for relatable comparisons:
- Driving 1 mile ≈ 0.41 kg CO₂
- Charging a smartphone ≈ 0.008 kg CO₂
- One hour of Netflix ≈ 0.036 kg CO₂
- A load of laundry ≈ 0.3 kg CO₂
- US grid average: 0.40 kg CO₂/kWh

ANALYZE each process for:
1. Energy efficiency relative to manufacturing industry norms
2. Carbon footprint significance (compare to everyday activities above)
3. Renewable energy potential (which processes benefit most from solar/wind?)
4. Specific energy reduction opportunities

RESPOND with ONLY valid JSON in this exact format:
{{
  "analyses": [
    {{
      "process": "FDM",
      "carbon_sub_score": <0-40 integer, higher=less carbon=better>,
      "energy_context": "how this compares to industry norms",
      "renewable_potential": "one sentence on renewable energy benefit",
      "reduction_opportunities": ["opportunity 1", "opportunity 2"],
      "carbon_comparison": "e.g., equivalent to driving 0.4 miles",
      "reasoning": "2-3 sentences explaining score with specific kWh and kg values"
    }},
    {{ "process": "SLA", ... }},
    {{ "process": "CNC", ... }},
    {{ "process": "Injection Molding", ... }}
  ]
}}

Reference actual kWh and kg CO₂ values from the data. Higher carbon = lower score."""

        response = await self._runner.run(input=prompt, model=DEDALUS_MODEL)
        return response.final_output

    async def _run_synthesizer(
        self,
        waste_data: list[dict],
        carbon_data: list[dict],
        env_analysis: str,
        energy_analysis: str,
        part_info: dict,
    ) -> str:
        """Agent 3: Sustainability Synthesizer — combines both analyses."""
        prompt = f"""You are the Chief Sustainability Officer synthesizing a multi-agent environmental assessment.

RAW CALCULATED DATA:
Waste per process: {json.dumps(waste_data, indent=2)}
Carbon per process: {json.dumps(carbon_data, indent=2)}

ENVIRONMENTAL IMPACT ANALYST FINDINGS:
{env_analysis}

ENERGY & EMISSIONS EXPERT FINDINGS:
{energy_analysis}

PART: {part_info.get('volume_cm3', 'unknown')} cm³

SYNTHESIZE both expert analyses into a final sustainability report.

For each process (FDM, SLA, CNC, Injection Molding), produce:
1. A final GREEN SCORE (1-100) combining: waste (40% weight), carbon (40%), recyclability (20%)
2. Letter grade: A (80+), B (65-79), C (50-64), D (35-49), F (below 35)
3. A 2-4 sentence justification referencing BOTH experts' findings
4. The most impactful contextual comparison from the experts

Also produce:
- OVERALL RECOMMENDATION: 3-5 persuasive sentences recommending the greenest process and why
- SUSTAINABILITY ROADMAP: 4-6 specific, actionable steps an engineer can take to reduce environmental impact
- TRADE-OFF ANALYSIS: Compare the top 2-3 processes head-to-head

RESPOND with ONLY valid JSON:
{{
  "process_scores": [
    {{
      "process": "FDM",
      "score": <1-100>,
      "grade": "A/B/C/D/F",
      "waste_sub_score": <0-40>,
      "carbon_sub_score": <0-40>,
      "recyclability_sub_score": <0-20>,
      "justification": "2-4 sentences",
      "strengths": ["...", "..."],
      "weaknesses": ["..."],
      "circular_economy_notes": "...",
      "contextual_comparison": "most impactful comparison"
    }}
  ],
  "greenest_process": "the highest-scored process name",
  "overall_recommendation": "3-5 persuasive sentences",
  "sustainability_roadmap": ["Step 1: ...", "Step 2: ...", "Step 3: ...", "Step 4: ..."],
  "trade_offs": [
    {{
      "process_a": "...",
      "process_b": "...",
      "winner": "...",
      "summary": "one sentence comparison",
      "environmental_delta": "specific numbers: waste saved, carbon saved"
    }}
  ],
  "confidence_note": "Based on standard material defaults and US grid average carbon intensity."
}}

RULES:
- Scores MUST be consistent with sub-scores (waste + carbon + recyclability ≈ total)
- greenest_process MUST match the highest-scored process
- The roadmap must reference THIS part's specific data, not generic advice
- Make recommendations compelling — this is for sustainability judges at a hackathon"""

        response = await self._runner.run(input=prompt, model=DEDALUS_MODEL)
        return response.final_output

    def _parse_synthesis(
        self, synthesis_raw: str, env_raw: str, energy_raw: str
    ) -> AISustainabilityReport:
        """Parse the synthesizer JSON into typed dataclasses."""
        cleaned = self._strip_json_fences(synthesis_raw)
        data = json.loads(cleaned)

        process_analyses = []
        for ps in data.get("process_scores", []):
            process_analyses.append(AIProcessAnalysis(
                process=ps["process"],
                score=int(ps["score"]),
                grade=ps["grade"],
                waste_sub_score=int(ps.get("waste_sub_score", 0)),
                carbon_sub_score=int(ps.get("carbon_sub_score", 0)),
                recyclability_sub_score=int(ps.get("recyclability_sub_score", 0)),
                justification=ps.get("justification", ""),
                strengths=ps.get("strengths", []),
                weaknesses=ps.get("weaknesses", []),
                circular_economy_notes=ps.get("circular_economy_notes", ""),
                contextual_comparison=ps.get("contextual_comparison", ""),
            ))

        trade_offs = []
        for to_data in data.get("trade_offs", []):
            trade_offs.append(AITradeOff(
                process_a=to_data["process_a"],
                process_b=to_data["process_b"],
                winner=to_data["winner"],
                summary=to_data["summary"],
                environmental_delta=to_data.get("environmental_delta", ""),
            ))

        agent_reasoning = {
            "environmental_analyst": env_raw,
            "energy_expert": energy_raw,
            "synthesizer": synthesis_raw,
        }

        return AISustainabilityReport(
            process_analyses=sorted(
                process_analyses, key=lambda a: a.score, reverse=True
            ),
            overall_recommendation=data.get("overall_recommendation", ""),
            sustainability_roadmap=data.get("sustainability_roadmap", []),
            trade_offs=trade_offs,
            agent_reasoning=agent_reasoning,
            greenest_process=data.get("greenest_process", ""),
            confidence_note=data.get("confidence_note", ""),
        )

    @staticmethod
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
