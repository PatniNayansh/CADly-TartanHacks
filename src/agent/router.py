"""Complexity-based model routing for Dedalus agent."""

from typing import Optional


def compute_complexity(
    triangle_count: Optional[int],
    body_count: int,
    issue_count: int,
    machine_description_length: int,
) -> float:
    """Score 0-100 for complexity to determine which model to use.

    Factors that increase complexity:
    - High triangle count (>50k mesh triangles)
    - Multiple bodies (assemblies)
    - Many violations (complex analysis required)
    - Long machine description (complex requirements)

    Args:
        triangle_count: Number of triangles in mesh (None for Fusion CAD)
        body_count: Number of solid bodies
        issue_count: Number of DFM violations detected
        machine_description_length: Length of machine description text

    Returns:
        Complexity score from 0.0 to 100.0
    """
    score = 0.0

    # Triangle count (mesh complexity)
    if triangle_count is not None:
        if triangle_count > 50000:
            score += 30
        elif triangle_count > 10000:
            score += 15
        elif triangle_count > 5000:
            score += 5

    # Body count (assembly complexity)
    if body_count > 3:
        score += 20
    elif body_count > 1:
        score += 10

    # Issue count (analysis complexity)
    if issue_count > 10:
        score += 25
    elif issue_count > 5:
        score += 15
    elif issue_count > 2:
        score += 5

    # Machine description length (requirement complexity)
    if machine_description_length > 200:
        score += 15
    elif machine_description_length > 100:
        score += 10
    elif machine_description_length > 50:
        score += 5

    return min(score, 100.0)


def pick_model(complexity: float) -> str:
    """Route to appropriate model based on complexity score.

    Routing strategy:
    - Low complexity (<40): google/gemini-2.0-flash-exp (fast, cheap, good for simple tasks)
    - High complexity (>=40): anthropic/claude-sonnet-4-5-20250929 (powerful, better reasoning)

    Args:
        complexity: Complexity score from compute_complexity()

    Returns:
        Model identifier string for Dedalus SDK
    """
    if complexity < 40:
        return "google/gemini-2.0-flash-exp"
    else:
        return "anthropic/claude-sonnet-4-5-20250929"


def pick_model_for_task(task: str) -> str:
    """Task-specific routing for sub-tasks within the analysis.

    Some tasks benefit from different models regardless of overall complexity:
    - Structured extraction (machine text parsing) → fast model
    - Synthesis and reasoning (final report generation) → powerful model

    Args:
        task: Task identifier ("parse_machine_text", "extract_geometry", "synthesize_report", etc.)

    Returns:
        Model identifier string for Dedalus SDK
    """
    # Fast model for simple extraction tasks
    if task in ["parse_machine_text", "extract_geometry", "parse_metadata"]:
        return "google/gemini-2.0-flash-exp"

    # Powerful model for reasoning tasks
    elif task in ["synthesize_report", "recommend_process", "design_review"]:
        return "anthropic/claude-sonnet-4-5-20250929"

    # Default to Sonnet for unknown tasks
    else:
        return "anthropic/claude-sonnet-4-5-20250929"


def get_model_info(model_id: str) -> dict:
    """Get metadata about a model for display/logging.

    Args:
        model_id: Model identifier

    Returns:
        Dictionary with model metadata
    """
    models = {
        "google/gemini-2.0-flash-exp": {
            "name": "Gemini 2.0 Flash",
            "provider": "Google",
            "speed": "very fast",
            "cost": "low",
            "best_for": "Simple extraction, structured output, quick analysis"
        },
        "anthropic/claude-sonnet-4-5-20250929": {
            "name": "Claude Sonnet 4.5",
            "provider": "Anthropic",
            "speed": "moderate",
            "cost": "moderate",
            "best_for": "Complex reasoning, synthesis, detailed analysis"
        }
    }

    return models.get(model_id, {
        "name": model_id,
        "provider": "Unknown",
        "speed": "unknown",
        "cost": "unknown",
        "best_for": "General use"
    })
