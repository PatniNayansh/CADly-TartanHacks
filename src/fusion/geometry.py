"""Typed geometry extraction from Fusion 360.

Wraps the geometry query HTTP endpoints and parses responses into
typed dataclasses. This is the primary data source for all DFM analysis.
"""

import logging
from typing import Optional

from .client import FusionClient
from src.models.geometry import Body, Face, Edge, Wall, Hole

logger = logging.getLogger(__name__)


class GeometryHelper:
    """Extract and parse geometry data from Fusion 360."""

    def __init__(self, client: FusionClient):
        self.client = client

    async def get_bodies(self) -> list[Body]:
        """Get all bodies with volume, area, bounding box, face/edge counts."""
        data = await self.client.get("get_body_properties")
        return [Body.from_dict(b) for b in data.get("bodies", [])]

    async def get_faces(self) -> list[Face]:
        """Get all faces with type, area, normal, radius, centroid."""
        data = await self.client.get("get_faces_info")
        return [Face.from_dict(f) for f in data.get("faces", [])]

    async def get_edges(self) -> list[Edge]:
        """Get all edges with type, length, radius, concavity."""
        data = await self.client.get("get_edges_info")
        return [Edge.from_dict(e) for e in data.get("edges", [])]

    async def get_walls(self) -> list[Wall]:
        """Detect wall pairs from face data (server-side).

        Finds parallel planar face pairs (same normal direction) that are
        close together. In a shelled body, inner and outer faces of the
        same wall share the same geometric normal direction.
        """
        faces = await self.get_faces()
        planar = [f for f in faces if f.face_type == "plane" and f.normal]

        # For each face, find closest parallel partner
        closest: dict[int, tuple[int, float, list[float]]] = {}
        for i, f1 in enumerate(planar):
            n1 = f1.normal
            for j in range(i + 1, len(planar)):
                f2 = planar[j]
                n2 = f2.normal
                # Check parallel (dot ≈ +1)
                dot = n1[0]*n2[0] + n1[1]*n2[1] + n1[2]*n2[2]
                if abs(dot - 1.0) > 0.05:
                    continue
                # Perpendicular distance between the two planes
                c1 = f1.centroid or [0, 0, 0]
                c2 = f2.centroid or [0, 0, 0]
                dx, dy, dz = c1[0]-c2[0], c1[1]-c2[1], c1[2]-c2[2]
                dist_cm = abs(n2[0]*dx + n2[1]*dy + n2[2]*dz)
                thickness_mm = round(dist_cm * 10, 2)
                if thickness_mm < 0.01:
                    continue  # same plane, skip
                centroid = [
                    round((c1[0]+c2[0])/2, 4),
                    round((c1[1]+c2[1])/2, 4),
                    round((c1[2]+c2[2])/2, 4),
                ]
                fi1, fi2 = f1.index, f2.index
                if fi1 not in closest or thickness_mm < closest[fi1][1]:
                    closest[fi1] = (fi2, thickness_mm, centroid)
                if fi2 not in closest or thickness_mm < closest[fi2][1]:
                    closest[fi2] = (fi1, thickness_mm, centroid)

        # Deduplicate pairs
        walls = []
        seen = set()
        for face_idx, (partner_idx, thickness_mm, centroid) in closest.items():
            pair = (min(face_idx, partner_idx), max(face_idx, partner_idx))
            if pair in seen:
                continue
            seen.add(pair)
            walls.append(Wall(
                face_index_1=pair[0],
                face_index_2=pair[1],
                thickness_mm=thickness_mm,
                centroid=centroid,
            ))
        return walls

    async def get_holes(self) -> list[Hole]:
        """Get all cylindrical holes with diameter, depth in mm."""
        data = await self.client.get("analyze_holes")
        return [Hole.from_dict(h) for h in data.get("holes", [])]

    async def get_all(self) -> dict:
        """Fetch all geometry data in one call. Returns dict with typed lists.

        This is the main entry point for DFM analysis -- gets everything
        needed to check all rules in a single batch of HTTP calls.
        """
        bodies = await self.get_bodies()
        faces = await self.get_faces()
        edges = await self.get_edges()
        walls = await self.get_walls()
        holes = await self.get_holes()

        first_body = bodies[0] if bodies else None

        return {
            "bodies": bodies,
            "faces": faces,
            "edges": edges,
            "walls": walls,
            "holes": holes,
            "body": first_body,
        }
