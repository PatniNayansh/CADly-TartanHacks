"""Formats review board output into UI-ready structure."""

import logging

logger = logging.getLogger(__name__)


def format_review_for_ui(review_data: dict) -> dict:
    """Convert raw review board output into UI-friendly format.

    Args:
        review_data: Dict with "agents" and "synthesis" keys from ReviewBoard.run_review()

    Returns:
        UI-ready dict with agents list, synthesis, and metadata.
    """
    agents = review_data.get("agents", {})
    synthesis = review_data.get("synthesis", {})

    # Build agent cards for UI
    agent_cards = []
    agent_icons = {
        "CNC Expert": "&#9881;",       # gear
        "FDM Expert": "&#9971;",       # printer-like
        "Materials Engineer": "&#9878;", # atom
        "Cost Optimizer": "&#128176;",  # money bag
    }

    for name, output in agents.items():
        card = {
            "name": name,
            "icon": agent_icons.get(name, "&#129302;"),
            "assessment": output.get("assessment", "No assessment available."),
            "score": output.get("score"),
            "concerns": output.get("concerns", []),
            "recommendations": output.get("recommendations", []),
            "error": output.get("error", False),
            "raw": output,
        }
        agent_cards.append(card)

    return {
        "agents": agent_cards,
        "synthesis": synthesis,
        "has_synthesis": "executive_summary" in synthesis and "error" not in synthesis,
    }
