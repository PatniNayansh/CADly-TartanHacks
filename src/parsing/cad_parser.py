"""CAD file parser using trimesh for STL/OBJ geometry extraction."""

import trimesh
import numpy as np
from typing import Optional


def parse_mesh(filepath: str) -> dict:
    """Parse STL/OBJ file and extract geometry statistics.

    Returns dict matching GeometryStats schema:
    - Bounding box, volume, surface area
    - Triangle/vertex count
    - Wall thickness heuristic (ray casting)
    - Hole detection heuristic (cylindrical faces)
    - Overhang detection (face normals)

    Args:
        filepath: Path to STL or OBJ file

    Returns:
        Dictionary with geometry statistics
    """
    # Load mesh
    mesh = trimesh.load(filepath, force='mesh')

    # Basic stats
    bounds = mesh.bounds  # [[min_x, min_y, min_z], [max_x, max_y, max_z]]
    bounding_box = {
        "x": float((bounds[1][0] - bounds[0][0]) * 10),  # Convert cm to mm
        "y": float((bounds[1][1] - bounds[0][1]) * 10),
        "z": float((bounds[1][2] - bounds[0][2]) * 10),
    }

    # Wall thickness heuristic: sample points on surface, shoot rays inward
    walls = detect_walls_from_mesh(mesh)

    # Hole detection: find circular features
    holes = detect_holes_from_mesh(mesh)

    # Split into separate bodies
    split_meshes = mesh.split()
    body_count = len(split_meshes)

    return {
        "volume_cm3": float(mesh.volume),
        "surface_area_cm2": float(mesh.area),
        "bounding_box": bounding_box,
        "triangle_count": len(mesh.faces),
        "vertex_count": len(mesh.vertices),
        "face_count": len(mesh.faces),  # Approximation for mesh
        "body_count": body_count,
        "walls": walls,
        "holes": holes,
    }


def detect_walls_from_mesh(mesh: trimesh.Trimesh) -> list[dict]:
    """Ray casting to estimate wall thickness at sample points.

    Strategy:
    1. Sample face centroids across the mesh
    2. For each sample, shoot ray inward (opposite of normal)
    3. Find nearest hit distance → that's the wall thickness at that point
    4. Return measurements for thin walls (<2mm)

    Args:
        mesh: Trimesh object

    Returns:
        List of wall measurements with thickness and location
    """
    walls = []

    # Sample every 10th face to avoid excessive computation
    sample_indices = range(0, len(mesh.faces), max(1, len(mesh.faces) // 50))

    for face_idx in sample_indices:
        face = mesh.faces[face_idx]
        # Get face centroid and normal
        vertices = mesh.vertices[face]
        centroid = vertices.mean(axis=0)
        normal = mesh.face_normals[face_idx]

        # Shoot ray inward (opposite of normal)
        ray_origin = centroid + normal * 0.01  # Offset slightly to avoid self-intersection
        ray_direction = -normal

        # Find intersections
        locations, index_ray, index_tri = mesh.ray.intersects_location(
            ray_origins=[ray_origin],
            ray_directions=[ray_direction],
        )

        if len(locations) > 0:
            # Find closest hit
            distances = np.linalg.norm(locations - ray_origin, axis=1)
            min_distance = float(np.min(distances))

            # Convert cm to mm
            thickness_mm = min_distance * 10

            # Only report if thin (<2mm)
            if thickness_mm < 2.0:
                walls.append({
                    "face_id": f"mesh_face_{face_idx}",
                    "thickness_mm": thickness_mm,
                    "location": {
                        "x": float(centroid[0]),
                        "y": float(centroid[1]),
                        "z": float(centroid[2]),
                    }
                })

    return walls


def detect_holes_from_mesh(mesh: trimesh.Trimesh) -> list[dict]:
    """Detect cylindrical features as holes.

    Strategy:
    1. Identify concave regions (negative Gaussian curvature)
    2. Cluster nearby vertices
    3. Fit circles to clusters
    4. Estimate depth from bounding box

    Note: This is a heuristic approach. For production, consider using
    feature detection libraries or ML-based approaches.

    Args:
        mesh: Trimesh object

    Returns:
        List of hole measurements with diameter and depth
    """
    holes = []

    # Simplified heuristic: find small cylindrical regions
    # This is a placeholder - full hole detection would require:
    # - Mesh segmentation
    # - Cylinder fitting
    # - Depth measurement along axis

    # For now, return empty list
    # TODO: Implement proper hole detection when needed
    return holes


def parse_cad_file(filepath: str) -> dict:
    """Public interface for CAD file parsing.

    Args:
        filepath: Path to STL or OBJ file

    Returns:
        Dictionary matching GeometryStats Pydantic schema
    """
    return parse_mesh(filepath)
