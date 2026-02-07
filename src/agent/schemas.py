"""Pydantic schemas for Dedalus agent structured output."""

from pydantic import BaseModel, Field
from typing import Optional


class GeometryStats(BaseModel):
    """Geometry statistics extracted from CAD file or live Fusion."""

    volume_cm3: float = Field(description="Part volume in cubic centimeters")
    surface_area_cm2: float = Field(description="Surface area in square centimeters")
    bounding_box: dict[str, float] = Field(description="Bounding box dimensions {x, y, z} in mm")
    triangle_count: Optional[int] = Field(default=None, description="Triangle count (mesh only)")
    vertex_count: Optional[int] = Field(default=None, description="Vertex count (mesh only)")
    face_count: int = Field(description="Number of faces")
    body_count: int = Field(description="Number of solid bodies")
    walls: list[dict] = Field(default_factory=list, description="Wall measurements")
    holes: list[dict] = Field(default_factory=list, description="Hole measurements")


class DFMFinding(BaseModel):
    """A single DFM violation or suggestion."""

    rule_id: str = Field(description="Rule identifier (e.g., FDM-001)")
    severity: str = Field(description="Severity level: critical, warning, or suggestion")
    message: str = Field(description="Human-readable violation description")
    current_value: float = Field(description="Actual measured value")
    required_value: float = Field(description="Required/recommended value")
    fixable: bool = Field(description="Whether auto-fix is available")
    process: str = Field(description="Manufacturing process this applies to")
    feature_id: Optional[str] = Field(default=None, description="Feature ID for auto-fix (edge/face/hole ID)")
    fix_suggestion: Optional[str] = Field(default=None, description="Suggested fix action")


class CostBreakdown(BaseModel):
    """Cost breakdown for a manufacturing process."""

    process: str = Field(description="Manufacturing process name")
    material_cost: float = Field(description="Cost of raw material in USD")
    machine_time_cost: float = Field(description="Cost of machine time in USD")
    setup_cost: float = Field(description="Setup/tooling cost in USD")
    total: float = Field(description="Total cost in USD")
    unit_cost: float = Field(description="Per-unit cost in USD")


class MachineRecommendation(BaseModel):
    """Machine recommendation with fit score."""

    name: str = Field(description="Machine name")
    type: str = Field(description="Machine type (FDM, SLA, CNC, etc.)")
    score: float = Field(description="Fit score 0-10")
    build_volume_fits: bool = Field(description="Whether part fits in build volume")
    reason: str = Field(description="Why this machine was recommended")
    limitations: list[str] = Field(default_factory=list, description="Machine limitations")


class MaterialRecommendation(BaseModel):
    """Material recommendation with property scores."""

    name: str = Field(description="Material name")
    process: str = Field(description="Compatible process")
    score: float = Field(description="Overall fit score 0-10")
    properties: dict[str, float] = Field(description="Property scores for spider chart")
    reason: str = Field(description="Why this material was recommended")


class FixSuggestion(BaseModel):
    """Auto-fix suggestion for a violation."""

    violation_rule_id: str = Field(description="Rule ID this fix addresses")
    fix_type: str = Field(description="Fix type: wall, hole, corner, etc.")
    description: str = Field(description="What the fix does")
    estimated_impact: str = Field(description="Expected impact on manufacturability")
    script_stub: Optional[str] = Field(default=None, description="Fusion 360 script code")


class DFMReport(BaseModel):
    """Final structured report from Dedalus agent analysis."""

    part_name: str = Field(description="Name of the analyzed part")
    geometry: GeometryStats = Field(description="Extracted geometry statistics")
    findings: list[DFMFinding] = Field(default_factory=list, description="All DFM findings")
    blocking_issues: list[DFMFinding] = Field(default_factory=list, description="Critical issues only")
    warnings: list[DFMFinding] = Field(default_factory=list, description="Warnings only")
    is_manufacturable: bool = Field(description="Whether part can be manufactured as-is")
    recommended_process: str = Field(description="Best manufacturing process for this part")
    cost_estimates: list[CostBreakdown] = Field(default_factory=list, description="Cost breakdown per process")
    machine_recommendations: list[dict] = Field(default_factory=list, description="Recommended machines")
    material_recommendations: list[dict] = Field(default_factory=list, description="Recommended materials")
    fix_suggestions: list[dict] = Field(default_factory=list, description="Auto-fix suggestions")
    summary: str = Field(description="Executive summary of analysis")


class StreamEvent(BaseModel):
    """SSE event structure for real-time progress updates."""

    type: str = Field(description="Event type: phase, finding, cost, recommendation, final, model_handoff")
    phase: Optional[str] = Field(default=None, description="Current analysis phase")
    message: str = Field(description="Human-readable status message")
    progress: float = Field(ge=0.0, le=1.0, description="Progress 0.0-1.0")
    data: Optional[dict] = Field(default=None, description="Event payload data")


class ModelHandoff(BaseModel):
    """Model handoff information for multi-model analysis."""

    from_model: Optional[str] = Field(default=None, description="Previous model (None if first)")
    to_model: str = Field(description="Current model being used")
    phase: str = Field(description="Analysis phase name")
    reason: str = Field(description="Why this model was chosen")
    estimated_cost: float = Field(description="Estimated cost for this phase in USD")


class AnalysisStrategy(BaseModel):
    """Analysis strategy configuration."""

    mode: str = Field(description="Strategy mode: auto, budget, quality, custom")
    extraction_model: Optional[str] = Field(default=None, description="Model for extraction phase")
    reasoning_model: Optional[str] = Field(default=None, description="Model for reasoning phase")
    estimated_total_cost: float = Field(default=0.0, description="Total estimated cost in USD")
