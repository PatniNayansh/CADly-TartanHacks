"""Mock Fusion MCP server for demo without Fusion 360.

This server provides realistic responses for testing the Dedalus agent
without requiring a live Fusion 360 connection.
"""

from fastmcp import FastMCP

mcp = FastMCP("Mock Fusion 360")


@mcp.tool()
def get_active_design_metadata() -> dict:
    """Get metadata about the active Fusion 360 design.

    Returns:
        Dictionary with part name, body count, modification date, units
    """
    return {
        "part_name": "Sample Test Part",
        "body_count": 1,
        "modified_date": "2026-02-07",
        "units": "mm",
        "description": "Mock part for testing Dedalus integration"
    }


@mcp.tool()
def export_body(format: str = "stl") -> dict:
    """Export body to file format.

    Args:
        format: File format ("stl", "obj", "step")

    Returns:
        Export result with filepath
    """
    # Return path to bundled sample file
    filepath = f"data/sample_part.{format.lower()}"

    return {
        "success": True,
        "filepath": filepath,
        "format": format,
        "file_size_bytes": 12480  # Mock size
    }


@mcp.tool()
def highlight_features(feature_ids: list[str]) -> dict:
    """Highlight features in Fusion 360 UI.

    Args:
        feature_ids: List of face/edge IDs to highlight

    Returns:
        Success status and count
    """
    return {
        "success": True,
        "highlighted_count": len(feature_ids),
        "message": f"Would highlight {len(feature_ids)} features (mock mode)"
    }


@mcp.tool()
def apply_edit(edit_spec: dict) -> dict:
    """Apply parametric edit to design.

    Args:
        edit_spec: Edit specification with type and parameters
            Example: {"type": "fillet", "radius": 1.5, "edge_ids": ["edge1"]}

    Returns:
        Edit result with success status
    """
    edit_type = edit_spec.get("type", "unknown")

    return {
        "success": True,
        "edit_type": edit_type,
        "message": f"Would apply {edit_type} edit (mock mode)",
        "changes_made": 1
    }


@mcp.tool()
def get_geometry_stats() -> dict:
    """Get geometry statistics from active design.

    Returns:
        Dictionary matching GeometryStats schema
    """
    return {
        "volume_cm3": 30.0,
        "surface_area_cm2": 94.0,
        "bounding_box": {"x": 50.0, "y": 30.0, "z": 20.0},
        "triangle_count": None,  # Not applicable for parametric CAD
        "vertex_count": None,
        "face_count": 14,
        "body_count": 1,
        "walls": [
            {
                "face_id": "face_123",
                "thickness_mm": 1.0,
                "location": {"x": 25.0, "y": 15.0, "z": 10.0}
            }
        ],
        "holes": [
            {
                "diameter_mm": 2.0,
                "depth_mm": 20.0,
                "location": {"x": 25.0, "y": 15.0, "z": 0.0}
            }
        ]
    }


if __name__ == "__main__":
    # Run MCP server with SSE transport on port 8000
    print("Starting Mock Fusion MCP Server on port 8000...")
    print("Available tools:")
    print("  - get_active_design_metadata()")
    print("  - export_body(format)")
    print("  - highlight_features(feature_ids)")
    print("  - apply_edit(edit_spec)")
    print("  - get_geometry_stats()")
    mcp.run(transport="sse", port=8000)
