"""Dedalus-powered DFM analysis orchestrator."""

from typing import AsyncGenerator, Optional
import json
import os
from src.agent.schemas import DFMReport, StreamEvent, GeometryStats
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
from src.agent.router import compute_complexity, pick_model

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
    ) -> AsyncGenerator[StreamEvent, None]:
        """Run full DFM analysis via Dedalus agent with streaming.

        Workflow:
        1. Parse geometry (from file or Fusion)
        2. Compute complexity → pick model
        3. Run Dedalus agent with all tools
        4. Agent calls tools as needed
        5. Validate final output against DFMReport schema
        6. Yield final report

        Args:
            cad_filepath: Path to uploaded STL/OBJ file (if file upload mode)
            machine_text: Natural language machine description
            use_fusion: If True, query live Fusion 360 instead of file
            process: Manufacturing process filter
            quantity: Production quantity

        Yields:
            StreamEvent objects for SSE streaming to browser
        """
        # Phase 1: Geometry extraction
        yield StreamEvent(
            type="phase",
            phase="geometry_extraction",
            message="Extracting geometry data...",
            progress=0.1,
            data=None
        )

        # Get geometry data
        if cad_filepath:
            geometry = parse_cad_file(cad_filepath)
            part_name = os.path.basename(cad_filepath).split('.')[0]
        elif use_fusion:
            geometry = await get_fusion_geometry()
            part_name = "Fusion Part"
        else:
            raise ValueError("Must provide either cad_filepath or use_fusion=True")

        # Phase 2: Complexity routing
        complexity = compute_complexity(
            triangle_count=geometry.get("triangle_count"),
            body_count=geometry.get("body_count", 1),
            issue_count=0,  # Don't know yet
            machine_description_length=len(machine_text) if machine_text else 0,
        )

        model = pick_model(complexity)

        yield StreamEvent(
            type="phase",
            phase="model_selection",
            message=f"Routed to {model} (complexity: {complexity:.1f}/100)",
            progress=0.2,
            data={"model": model, "complexity": complexity}
        )

        # Phase 3: Build analysis prompt
        prompt = self._build_analysis_prompt(
            part_name=part_name,
            geometry=geometry,
            machine_text=machine_text,
            process=process,
            quantity=quantity
        )

        # Phase 4: Run Dedalus agent
        yield StreamEvent(
            type="phase",
            phase="dfm_analysis",
            message="Running DFM analysis with AI agent...",
            progress=0.3,
            data=None
        )

        # Create Dedalus runner
        runner = DedalusRunner(self.client)

        # Tool list - Dedalus will call these as needed
        tools = [
            parse_cad_file,
            check_dfm_rules,
            estimate_manufacturing_cost,
            recommend_machines,
            recommend_materials,
            suggest_fixes,
        ]

        # Add async tools if needed
        if machine_text:
            tools.append(parse_machine_capabilities)

        # Run agent (non-streaming for simplicity)
        # TODO: Implement streaming mode to get real-time tool calls
        response = await runner.run(
            input=prompt,
            model=model,
            tools=tools,
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

        # Phase 6: Final report
        yield StreamEvent(
            type="final",
            phase="complete",
            message="Analysis complete",
            progress=1.0,
            data=report.model_dump()
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
