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


def get_strategy_models(strategy: str, extraction_model: str = None, reasoning_model: str = None) -> dict:
    """Get models for each phase based on strategy mode.

    Args:
        strategy: Strategy mode ("auto", "budget", "quality", "custom")
        extraction_model: Custom model for extraction phase (only for "custom" mode)
        reasoning_model: Custom model for reasoning phase (only for "custom" mode)

    Returns:
        Dictionary with extraction_model and reasoning_model
    """
    if strategy == "auto":
        # Smart handoff: Fast for extraction, powerful for reasoning
        return {
            "extraction_model": "google/gemini-2.0-flash-exp",
            "reasoning_model": "anthropic/claude-sonnet-4-5-20250929",
            "reason": "Optimal cost/quality balance"
        }
    elif strategy == "budget":
        # All Gemini Flash: cheapest option
        return {
            "extraction_model": "google/gemini-2.0-flash-exp",
            "reasoning_model": "google/gemini-2.0-flash-exp",
            "reason": "Minimum cost"
        }
    elif strategy == "quality":
        # All Claude Sonnet: highest quality
        return {
            "extraction_model": "anthropic/claude-sonnet-4-5-20250929",
            "reasoning_model": "anthropic/claude-sonnet-4-5-20250929",
            "reason": "Maximum quality"
        }
    elif strategy == "custom":
        # User-specified models
        return {
            "extraction_model": extraction_model or "google/gemini-2.0-flash-exp",
            "reasoning_model": reasoning_model or "anthropic/claude-sonnet-4-5-20250929",
            "reason": "User-defined"
        }
    else:
        # Default to auto
        return get_strategy_models("auto")


def estimate_phase_cost(model_id: str, tokens_estimated: int = 1000) -> float:
    """Estimate cost for a phase based on model and token count.

    Args:
        model_id: Model identifier
        tokens_estimated: Estimated tokens for this phase

    Returns:
        Estimated cost in USD
    """
    # Rough cost estimates per 1M tokens (as of 2026)
    costs_per_million = {
        "google/gemini-2.0-flash-exp": 0.10,                    # Very cheap
        "anthropic/claude-haiku-4-5-20251001": 0.40,           # Fast & cheap
        "anthropic/claude-sonnet-4-5-20250929": 3.00,          # Balanced
        "claude-opus-4-5-20251101": 15.00,                     # Most powerful
        "anthropic/claude-opus-4-6": 15.00,                    # Legacy Opus
    }

    cost_per_million = costs_per_million.get(model_id, 1.0)
    return (tokens_estimated / 1_000_000) * cost_per_million


def estimate_total_cost(extraction_model: str, reasoning_model: str) -> dict:
    """Estimate total cost for full analysis.

    Args:
        extraction_model: Model for extraction phase
        reasoning_model: Model for reasoning phase

    Returns:
        Dictionary with cost breakdown
    """
    # Estimate token usage per phase
    extraction_tokens = 2000  # Geometry + machine text parsing
    reasoning_tokens = 5000   # Full DFM analysis + synthesis

    extraction_cost = estimate_phase_cost(extraction_model, extraction_tokens)
    reasoning_cost = estimate_phase_cost(reasoning_model, reasoning_tokens)

    return {
        "extraction_cost": extraction_cost,
        "reasoning_cost": reasoning_cost,
        "total_cost": extraction_cost + reasoning_cost,
        "breakdown": {
            "extraction": {
                "model": extraction_model,
                "tokens": extraction_tokens,
                "cost": extraction_cost
            },
            "reasoning": {
                "model": reasoning_model,
                "tokens": reasoning_tokens,
                "cost": reasoning_cost
            }
        }
    }


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
        "anthropic/claude-haiku-4-5-20251001": {
            "name": "Claude Haiku 4.5",
            "provider": "Anthropic",
            "speed": "very fast",
            "cost": "low",
            "best_for": "Fast extraction, simple reasoning, quick analysis"
        },
        "anthropic/claude-sonnet-4-5-20250929": {
            "name": "Claude Sonnet 4.5",
            "provider": "Anthropic",
            "speed": "moderate",
            "cost": "moderate",
            "best_for": "Complex reasoning, synthesis, detailed analysis"
        },
        "claude-opus-4-5-20251101": {
            "name": "Claude Opus 4.5",
            "provider": "Anthropic",
            "speed": "slower",
            "cost": "high",
            "best_for": "Most complex reasoning, highest quality analysis"
        }
    }

    return models.get(model_id, {
        "name": model_id,
        "provider": "Unknown",
        "speed": "unknown",
        "cost": "unknown",
        "best_for": "General use"
    })
