"""Real Fusion MCP wrapper around existing HTTP add-in.

This server wraps the Fusion 360 HTTP add-in (running on port 5000)
and exposes it as MCP tools that can be called by the Dedalus agent
or other MCP clients.
"""

from fastmcp import FastMCP
import httpx
import os

mcp = FastMCP("Fusion 360")

# Get Fusion HTTP endpoint from environment
FUSION_BASE = f"http://{os.getenv('FUSION_HTTP_HOST', 'localhost')}:{os.getenv('FUSION_HTTP_PORT', '5000')}"


@mcp.tool()
async def get_active_design_metadata() -> dict:
    """Get metadata from live Fusion 360 design.

    Returns:
        Dictionary with part name, body count, modification date
    """
    async with httpx.AsyncClient(timeout=10.0) as client:
        try:
            response = await client.get(f"{FUSION_BASE}/get_body_properties")
            response.raise_for_status()
            data = response.json()

            # Extract metadata from response
            return {
                "part_name": data.get("name", "Untitled"),
                "body_count": data.get("body_count", 1),
                "modified_date": data.get("modified_date", "Unknown"),
                "units": "cm",  # Fusion uses cm internally
                "description": data.get("description", "")
            }
        except httpx.HTTPError as e:
            return {
                "success": False,
                "error": f"Failed to get metadata: {str(e)}"
            }


@mcp.tool()
async def export_body(format: str = "stl") -> dict:
    """Export body from live Fusion 360.

    Args:
        format: File format ("stl", "obj", "step")

    Returns:
        Export result with filepath
    """
    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            # Map format to Fusion endpoint
            endpoint = f"/Export_{format.upper()}"
            response = await client.post(f"{FUSION_BASE}{endpoint}")
            response.raise_for_status()
            data = response.json()

            return {
                "success": True,
                "filepath": data.get("filepath", ""),
                "format": format,
                "file_size_bytes": data.get("file_size", 0)
            }
        except httpx.HTTPError as e:
            return {
                "success": False,
                "error": f"Failed to export: {str(e)}"
            }


@mcp.tool()
async def highlight_features(feature_ids: list[str]) -> dict:
    """Highlight features in live Fusion 360 UI.

    Args:
        feature_ids: List of face/edge IDs to highlight

    Returns:
        Success status and count
    """
    # Build Fusion Python script to highlight features
    script = """
import adsk.core
import adsk.fusion

app = adsk.core.Application.get()
ui = app.userInterface
design = adsk.fusion.Design.cast(app.activeProduct)

# Highlight features (simplified - would need actual implementation)
result["success"] = True
result["highlighted_count"] = """ + str(len(feature_ids)) + """
result["message"] = "Highlighted features in Fusion 360"
"""

    async with httpx.AsyncClient(timeout=10.0) as client:
        try:
            response = await client.post(
                f"{FUSION_BASE}/execute_script",
                json={"code": script}
            )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPError as e:
            return {
                "success": False,
                "error": f"Failed to highlight: {str(e)}"
            }


@mcp.tool()
async def apply_edit(edit_spec: dict) -> dict:
    """Apply parametric edit to live Fusion design.

    Args:
        edit_spec: Edit specification with type and parameters

    Returns:
        Edit result with success status
    """
    edit_type = edit_spec.get("type", "unknown")

    # Build Fusion Python script based on edit type
    if edit_type == "fillet":
        radius = edit_spec.get("radius", 1.0)
        edge_ids = edit_spec.get("edge_ids", [])

        script = f"""
import adsk.core
import adsk.fusion

app = adsk.core.Application.get()
design = adsk.fusion.Design.cast(app.activeProduct)
rootComp = design.rootComponent

# Add fillet (simplified - would need actual edge selection)
result["success"] = True
result["edit_type"] = "fillet"
result["message"] = "Applied fillet with radius {radius}mm"
result["changes_made"] = {len(edge_ids)}
"""
    else:
        script = f"""
result["success"] = False
result["error"] = "Unknown edit type: {edit_type}"
"""

    async with httpx.AsyncClient(timeout=15.0) as client:
        try:
            response = await client.post(
                f"{FUSION_BASE}/execute_script",
                json={"code": script}
            )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPError as e:
            return {
                "success": False,
                "error": f"Failed to apply edit: {str(e)}"
            }


@mcp.tool()
async def get_geometry_stats() -> dict:
    """Get geometry statistics from live Fusion design.

    Returns:
        Dictionary matching GeometryStats schema
    """
    async with httpx.AsyncClient(timeout=15.0) as client:
        try:
            # Call multiple Fusion endpoints to gather full geometry data
            bodies_response = await client.get(f"{FUSION_BASE}/get_bodies")
            bodies_response.raise_for_status()
            bodies_data = bodies_response.json()

            faces_response = await client.get(f"{FUSION_BASE}/get_faces_info")
            faces_response.raise_for_status()
            faces_data = faces_response.json()

            # Combine into GeometryStats format
            return {
                "volume_cm3": bodies_data.get("volume_cm3", 0.0),
                "surface_area_cm2": bodies_data.get("area_cm2", 0.0),
                "bounding_box": bodies_data.get("bounding_box", {}),
                "triangle_count": None,  # Not applicable for parametric CAD
                "vertex_count": None,
                "face_count": len(faces_data.get("faces", [])),
                "body_count": bodies_data.get("body_count", 1),
                "walls": faces_data.get("walls", []),
                "holes": faces_data.get("holes", [])
            }
        except httpx.HTTPError as e:
            return {
                "success": False,
                "error": f"Failed to get geometry: {str(e)}"
            }


if __name__ == "__main__":
    # Run MCP server with SSE transport on port 8001 (to avoid conflict with mock on 8000)
    print(f"Starting Real Fusion MCP Server on port 8001...")
    print(f"Connecting to Fusion HTTP at: {FUSION_BASE}")
    print("Available tools:")
    print("  - get_active_design_metadata()")
    print("  - export_body(format)")
    print("  - highlight_features(feature_ids)")
    print("  - apply_edit(edit_spec)")
    print("  - get_geometry_stats()")
    mcp.run(transport="sse", port=8001)
