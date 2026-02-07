"""Typed async wrappers for Fusion 360 HTTP endpoints.

Each function maps to a specific endpoint on the Fusion add-in (port 5000).
These replace the 41 MCP tools from the old MCP_Server.py.
"""

from typing import Optional
from .client import FusionClient


# --- CAD Creation ---

async def create_box(
    client: FusionClient,
    height: float, width: float, depth: float,
    x: float = 0, y: float = 0, z: float = 0,
    plane: str = "XY",
) -> dict:
    """Create a rectangular box."""
    return await client.post("box", {
        "height": height, "width": width, "depth": depth,
        "x": x, "y": y, "z": z, "plane": plane,
    })


async def create_cylinder(
    client: FusionClient,
    radius: float, height: float,
    x: float = 0, y: float = 0, z: float = 0,
    plane: str = "XY",
) -> dict:
    """Create a cylinder."""
    return await client.post("cylinder", {
        "radius": radius, "height": height,
        "x": x, "y": y, "z": z, "plane": plane,
    })


async def create_circle(
    client: FusionClient,
    radius: float,
    x: float = 0, y: float = 0, z: float = 0,
    plane: str = "XY",
) -> dict:
    """Draw a 2D circle on a sketch."""
    return await client.post("circle", {
        "radius": radius, "x": x, "y": y, "z": z, "plane": plane,
    })


async def create_rectangle(
    client: FusionClient,
    x1: float, y1: float, z1: float,
    x2: float, y2: float, z2: float,
    plane: str = "XY",
) -> dict:
    """Draw a 2D rectangle."""
    return await client.post("rectangle", {
        "x_1": x1, "y_1": y1, "z_1": z1,
        "x_2": x2, "y_2": y2, "z_2": z2,
        "plane": plane,
    })


async def create_sphere(
    client: FusionClient,
    radius: float,
    x: float = 0, y: float = 0, z: float = 0,
) -> dict:
    """Create a sphere."""
    return await client.post("sphere", {
        "radius": radius, "x": x, "y": y, "z": z,
    })


# --- Features ---

async def extrude(client: FusionClient, value: float, taper_angle: float = 0) -> dict:
    """Extrude the last sketch."""
    return await client.post("extrude", {"value": value, "taperangle": taper_angle})


async def cut_extrude(client: FusionClient, depth: float) -> dict:
    """Cut-extrude (negative direction)."""
    return await client.post("cut_extrude", {"depth": depth})


async def revolve(client: FusionClient, angle: float = 360) -> dict:
    """Revolve the last profile around an axis."""
    return await client.post("revolve", {"angle": angle})


async def sweep(client: FusionClient) -> dict:
    """Sweep the last profile along the last spline path."""
    return await client.post("sweep", {})


async def loft(client: FusionClient, sketch_count: int) -> dict:
    """Loft between sketches."""
    return await client.post("loft", {"sketchcount": sketch_count})


async def fillet_edges(client: FusionClient, radius: float) -> dict:
    """Fillet all edges with given radius."""
    return await client.post("fillet_edges", {"radius": radius})


async def fillet_specific_edges(
    client: FusionClient, edge_indices: list[int], radius: float,
) -> dict:
    """Fillet specific edges by index."""
    return await client.post("fillet_specific_edges", {
        "edge_indices": edge_indices, "radius": radius,
    })


async def shell_body(client: FusionClient, thickness: float, face_index: int = 0) -> dict:
    """Shell a body (hollow it out)."""
    return await client.post("shell_body", {"thickness": thickness, "faceindex": face_index})


async def create_holes(
    client: FusionClient,
    points: list, width: float, depth: float, face_index: int = 0,
) -> dict:
    """Create holes at specified points on a face."""
    return await client.post("holes", {
        "points": points, "width": width, "depth": depth, "faceindex": face_index,
    })


# --- Patterns ---

async def circular_pattern(
    client: FusionClient, quantity: int, axis: str = "Z", plane: str = "XY",
) -> dict:
    """Create a circular pattern."""
    return await client.post("circular_pattern", {
        "quantity": quantity, "axis": axis, "plane": plane,
    })


async def rectangular_pattern(
    client: FusionClient,
    qty1: int, dist1: float, axis1: str,
    qty2: int, dist2: float, axis2: str,
    plane: str = "XY",
) -> dict:
    """Create a rectangular pattern."""
    return await client.post("rectangular_pattern", {
        "quantity_one": qty1, "distance_one": dist1, "axis_one": axis1,
        "quantity_two": qty2, "distance_two": dist2, "axis_two": axis2,
        "plane": plane,
    })


# --- Operations ---

async def boolean_operation(client: FusionClient, operation: str) -> dict:
    """Boolean operation: 'join', 'cut', or 'intersect'."""
    return await client.post("boolean_operation", {"operation": operation})


async def move_body(client: FusionClient, x: float, y: float, z: float) -> dict:
    """Move the latest body."""
    return await client.post("move_body", {"x": x, "y": y, "z": z})


async def set_parameter(client: FusionClient, name: str, value: float) -> dict:
    """Set a model parameter by name."""
    return await client.post("set_parameter", {"name": name, "value": value})


async def undo(client: FusionClient) -> dict:
    """Undo the last operation."""
    return await client.undo()


# --- Export ---

async def export_step(client: FusionClient, name: str) -> dict:
    """Export the model as a STEP file."""
    return await client.post("export_step", {"name": name})


async def export_stl(client: FusionClient, name: str) -> dict:
    """Export the model as an STL file."""
    return await client.post("export_stl", {"name": name})


# --- Scene Management ---

async def delete_all(client: FusionClient) -> dict:
    """Delete everything in the scene."""
    return await client.post("delete_all", {})
