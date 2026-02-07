"""Dedalus-powered DFM analysis orchestrator."""

from typing import AsyncGenerator, Optional
import json
import os
from src.agent.schemas import DFMReport, StreamEvent, GeometryStats, ModelHandoff
from src.agent.tools import (
    parse_cad_file,
    get_fusion_geometry,
    check_dfm_rules,
    parse_machine_capabilities,
    estimate_manufacturing_cost,
    recommend_machines,
    recommend_materials,
    suggest_fixes,
    highlight_in_fusion,
)
from src.agent.router import (
    compute_complexity,
    pick_model,
    get_strategy_models,
    estimate_total_cost,
    estimate_phase_cost,
    get_model_info
)

# Lazy import for Dedalus - graceful degradation if not installed
try:
    from dedalus_labs import AsyncDedalus, DedalusRunner
    DEDALUS_AVAILABLE = True
except ImportError:
    DEDALUS_AVAILABLE = False
    AsyncDedalus = None
    DedalusRunner = None


class DFMAgent:
    """Main Dedalus-powered DFM analysis orchestrator.

    This class coordinates the entire DFM analysis workflow using the Dedalus SDK.
    It yields StreamEvents for real-time SSE progress updates to the UI.
    """

    def __init__(self):
        """Initialize the DFM agent with Dedalus client."""
        if not DEDALUS_AVAILABLE:
            raise ImportError(
                "dedalus-labs package not installed. "
                "Install with: pip install dedalus-labs"
            )

        # Initialize Dedalus client (reads DEDALUS_API_KEY from env)
        self.client = AsyncDedalus()

    async def analyze(
        self,
        cad_filepath: Optional[str] = None,
        machine_text: Optional[str] = None,
        use_fusion: bool = False,
        process: str = "all",
        quantity: int = 1,
        strategy: str = "auto",
        extraction_model: Optional[str] = None,
        reasoning_model: Optional[str] = None,
    ) -> AsyncGenerator[StreamEvent, None]:
        """Run full DFM analysis via Dedalus agent with multi-model streaming.

        Workflow:
        1. Parse geometry (from file or Fusion)
        2. Get strategy models (auto/budget/quality/custom)
        3. **PHASE 1** (Extraction): Fast model for geometry + machine parsing
        4. **MODEL HANDOFF** 🔄
        5. **PHASE 2** (Reasoning): Powerful model for DFM synthesis
        6. Validate final output against DFMReport schema
        7. Yield final report with cost savings

        Args:
            cad_filepath: Path to uploaded STL/OBJ file (if file upload mode)
            machine_text: Natural language machine description
            use_fusion: If True, query live Fusion 360 instead of file
            process: Manufacturing process filter
            quantity: Production quantity
            strategy: Model strategy ("auto", "budget", "quality", "custom")
            extraction_model: Custom model for extraction (only for "custom" strategy)
            reasoning_model: Custom model for reasoning (only for "custom" strategy)

        Yields:
            StreamEvent objects for SSE streaming to browser
        """
        # Step 0: Get geometry data first
        yield StreamEvent(
            type="phase",
            phase="geometry_extraction",
            message="Extracting geometry data...",
            progress=0.05,
            data=None
        )

        if cad_filepath:
            geometry = parse_cad_file(cad_filepath)
            part_name = os.path.basename(cad_filepath).split('.')[0]
        elif use_fusion:
            geometry = await get_fusion_geometry()
            part_name = "Fusion Part"
        else:
            raise ValueError("Must provide either cad_filepath or use_fusion=True")

        # Step 1: Determine model strategy
        models = get_strategy_models(strategy, extraction_model, reasoning_model)
        extraction_model_id = models["extraction_model"]
        reasoning_model_id = models["reasoning_model"]

        # Estimate costs
        cost_breakdown = estimate_total_cost(extraction_model_id, reasoning_model_id)

        yield StreamEvent(
            type="phase",
            phase="strategy_selection",
            message=f"Strategy: {strategy.upper()} | Est. cost: ${cost_breakdown['total_cost']:.4f}",
            progress=0.1,
            data={
                "strategy": strategy,
                "models": models,
                "cost_breakdown": cost_breakdown
            }
        )

        # === PHASE 1: EXTRACTION (Fast Model) ===
        yield StreamEvent(
            type="model_handoff",
            phase="extraction_start",
            message=f"🚀 PHASE 1: Starting extraction with {get_model_info(extraction_model_id)['name']}",
            progress=0.15,
            data=ModelHandoff(
                from_model=None,
                to_model=extraction_model_id,
                phase="extraction",
                reason=f"Fast extraction of geometry and machine data ({models['reason']})",
                estimated_cost=cost_breakdown['extraction_cost']
            ).model_dump()
        )

        # Build extraction prompt
        extraction_prompt = f"""You are a data extraction expert. Extract and structure this information:

PART GEOMETRY:
{json.dumps(geometry, indent=2)}

MACHINE TEXT:
{machine_text or "No machines specified"}

YOUR TASKS:
1. If machine text is provided, call parse_machine_capabilities() to extract structured machine data
2. Return a JSON summary of the geometry and available machines

Return ONLY valid JSON matching this format:
{{
  "geometry_summary": "Brief description of the part",
  "machines_available": ["list of machine names"] or [],
  "ready_for_analysis": true
}}"""

        # Create extraction runner
        extraction_runner = DedalusRunner(self.client)

        # Run extraction phase
        extraction_tools = []
        if machine_text:
            extraction_tools.append(parse_machine_capabilities)

        extraction_response = await extraction_runner.run(
            input=extraction_prompt,
            model=extraction_model_id,
            tools=extraction_tools,
            stream=False,
        )

        yield StreamEvent(
            type="phase",
            phase="extraction_complete",
            message="✅ Extraction complete",
            progress=0.35,
            data={"extraction_output": extraction_response.final_output[:200]}
        )

        # === MODEL HANDOFF ===
        if extraction_model_id != reasoning_model_id:
            yield StreamEvent(
                type="model_handoff",
                phase="handoff",
                message=f"🔄 MODEL HANDOFF: {get_model_info(extraction_model_id)['name']} → {get_model_info(reasoning_model_id)['name']}",
                progress=0.4,
                data=ModelHandoff(
                    from_model=extraction_model_id,
                    to_model=reasoning_model_id,
                    phase="reasoning",
                    reason=f"Deep DFM analysis and synthesis ({models['reason']})",
                    estimated_cost=cost_breakdown['reasoning_cost']
                ).model_dump()
            )

        # === PHASE 2: REASONING (Powerful Model) ===
        yield StreamEvent(
            type="phase",
            phase="dfm_analysis",
            message=f"🧠 PHASE 2: Running DFM analysis with {get_model_info(reasoning_model_id)['name']}",
            progress=0.45,
            data=None
        )

        # Build reasoning prompt
        reasoning_prompt = self._build_analysis_prompt(
            part_name=part_name,
            geometry=geometry,
            machine_text=machine_text,
            process=process,
            quantity=quantity
        )

        # Append extraction results if available
        reasoning_prompt += f"\n\nEXTRACTION PHASE RESULTS:\n{extraction_response.final_output}\n"

        # Create reasoning runner
        reasoning_runner = DedalusRunner(self.client)

        # Reasoning tools
        reasoning_tools = [
            check_dfm_rules,
            estimate_manufacturing_cost,
            recommend_machines,
            recommend_materials,
            suggest_fixes,
        ]

        # Run reasoning phase
        response = await reasoning_runner.run(
            input=reasoning_prompt,
            model=reasoning_model_id,
            tools=reasoning_tools,
            stream=False,
        )

        # Phase 5: Parse and validate output
        yield StreamEvent(
            type="phase",
            phase="validation",
            message="Validating analysis results...",
            progress=0.9,
            data=None
        )

        # Try to parse structured JSON output
        try:
            # Extract JSON from response
            output_text = response.final_output

            # Try to find JSON in the output
            if '{' in output_text:
                # Find the JSON object
                start_idx = output_text.find('{')
                # Simple heuristic: find matching closing brace
                brace_count = 0
                end_idx = start_idx
                for i, char in enumerate(output_text[start_idx:], start=start_idx):
                    if char == '{':
                        brace_count += 1
                    elif char == '}':
                        brace_count -= 1
                        if brace_count == 0:
                            end_idx = i + 1
                            break

                json_str = output_text[start_idx:end_idx]
                report_data = json.loads(json_str)

                # Validate against Pydantic schema
                report = DFMReport(**report_data)
            else:
                # Fallback if no JSON found
                report = self._parse_text_output(output_text, part_name, geometry)

        except (json.JSONDecodeError, Exception) as e:
            # Fallback parsing
            print(f"Failed to parse structured output: {e}")
            report = self._parse_text_output(
                response.final_output,
                part_name,
                geometry
            )

        # Phase 6: Calculate cost savings
        all_sonnet_cost = estimate_total_cost(
            "anthropic/claude-sonnet-4-5-20250929",
            "anthropic/claude-sonnet-4-5-20250929"
        )["total_cost"]

        savings = all_sonnet_cost - cost_breakdown["total_cost"]
        savings_percent = (savings / all_sonnet_cost * 100) if all_sonnet_cost > 0 else 0

        # Phase 7: Final report
        final_data = report.model_dump()
        final_data["cost_analysis"] = {
            "strategy": strategy,
            "extraction_model": extraction_model_id,
            "reasoning_model": reasoning_model_id,
            "total_cost": cost_breakdown["total_cost"],
            "all_sonnet_cost": all_sonnet_cost,
            "savings": savings,
            "savings_percent": savings_percent,
            "breakdown": cost_breakdown["breakdown"]
        }

        yield StreamEvent(
            type="final",
            phase="complete",
            message=f"✅ Analysis complete! Saved ${savings:.4f} ({savings_percent:.1f}%) vs all-Sonnet",
            progress=1.0,
            data=final_data
        )

    def _build_analysis_prompt(
        self,
        part_name: str,
        geometry: dict,
        machine_text: Optional[str],
        process: str,
        quantity: int
    ) -> str:
        """Construct the agent prompt for DFM analysis.

        Args:
            part_name: Name of the part
            geometry: Geometry statistics dict
            machine_text: Optional machine description
            process: Manufacturing process filter
            quantity: Production quantity

        Returns:
            Formatted prompt string
        """
        prompt = f"""You are a DFM (Design for Manufacturing) analysis expert. Analyze this CAD part for manufacturability.

PART INFORMATION:
- Name: {part_name}
- Volume: {geometry.get('volume_cm3', 0):.2f} cm³
- Surface Area: {geometry.get('surface_area_cm2', 0):.2f} cm²
- Bounding Box: {geometry.get('bounding_box', {})}
- Body Count: {geometry.get('body_count', 1)}

ANALYSIS PARAMETERS:
- Target process: {process}
- Production quantity: {quantity} units
"""

        if machine_text:
            prompt += f"""
AVAILABLE MACHINES:
{machine_text}

First, parse the machine descriptions using the parse_machine_capabilities tool.
"""

        prompt += """
ANALYSIS WORKFLOW:

1. Call check_dfm_rules() to analyze the geometry for manufacturing violations
2. Call estimate_manufacturing_cost() for each viable manufacturing process
3. Call recommend_machines() to match available machines to this part
4. Call recommend_materials() to suggest suitable materials
5. Call suggest_fixes() to generate fix recommendations for violations

OUTPUT REQUIREMENTS:

Return a valid JSON object matching this exact schema:

{
  "part_name": "string",
  "geometry": {
    "volume_cm3": number,
    "surface_area_cm2": number,
    "bounding_box": {"x": number, "y": number, "z": number},
    "triangle_count": number or null,
    "vertex_count": number or null,
    "face_count": number,
    "body_count": number,
    "walls": [],
    "holes": []
  },
  "findings": [
    {
      "rule_id": "string",
      "severity": "critical | warning | suggestion",
      "message": "string",
      "current_value": number,
      "required_value": number,
      "fixable": boolean,
      "process": "string",
      "feature_id": "string or null - edge/face/hole ID for auto-fix",
      "fix_suggestion": "string or null"
    }
  ],
  "blocking_issues": [],
  "warnings": [],
  "is_manufacturable": boolean,
  "recommended_process": "fdm | sla | cnc | injection_molding",
  "cost_estimates": [
    {
      "process": "string",
      "material_cost": number,
      "machine_time_cost": number,
      "setup_cost": number,
      "total": number,
      "unit_cost": number
    }
  ],
  "machine_recommendations": [],
  "material_recommendations": [],
  "fix_suggestions": [],
  "summary": "string - executive summary of analysis"
}

Be thorough. Call each tool with correct parameters. Report ALL findings.
The JSON MUST be valid and match the schema exactly.
"""
        return prompt

    def _parse_text_output(
        self,
        text: str,
        part_name: str,
        geometry: dict
    ) -> DFMReport:
        """Fallback parser if agent returns text instead of valid JSON.

        Args:
            text: Agent output text
            part_name: Part name
            geometry: Geometry dict

        Returns:
            DFMReport with best-effort parsing
        """
        # Validate geometry matches schema
        geo_stats = GeometryStats(**geometry)

        # Create minimal valid report
        return DFMReport(
            part_name=part_name,
            geometry=geo_stats,
            findings=[],
            blocking_issues=[],
            warnings=[],
            is_manufacturable=True,
            recommended_process="fdm",
            cost_estimates=[],
            machine_recommendations=[],
            material_recommendations=[],
            fix_suggestions=[],
            summary=f"Analysis incomplete. Agent output: {text[:500]}"
        )
