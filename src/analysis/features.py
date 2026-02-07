"""General feature extraction from geometry data.

Identifies feature types (pockets, bosses, through-holes, blind-holes)
from the raw face/edge data. Used by the simulator and report generator
to provide human-readable feature descriptions.
"""

import logging
from dataclasses import dataclass
from typing import Optional

from src.models.geometry import Face, Edge, Wall, Hole

logger = logging.getLogger(__name__)


@dataclass
class Feature:
    """An identified geometric feature."""
    feature_type: str  # "pocket", "boss", "through_hole", "blind_hole", "wall", "fillet", "chamfer"
    description: str
    face_indices: list[int]
    edge_indices: list[int]
    dimensions: dict  # e.g. {"depth_mm": 10, "width_mm": 5}


class FeatureExtractor:
    """Extract and classify geometric features from analysis data."""

    def extract(
        self,
        faces: list[Face],
        edges: list[Edge],
        walls: list[Wall],
        holes: list[Hole],
    ) -> list[Feature]:
        """Identify features from geometry data.

        This is a simplified feature extractor that categorizes geometry
        into common manufacturing feature types.
        """
        features = []

        # Classify holes
        for hole in holes:
            if hole.depth_to_diameter_ratio > 10:
                feat_type = "deep_hole"
                desc = f"Deep hole: {hole.diameter_mm:.1f}mm dia x {hole.depth_mm:.1f}mm deep"
            elif hole.depth_mm > 0:
                feat_type = "blind_hole"
                desc = f"Blind hole: {hole.diameter_mm:.1f}mm dia x {hole.depth_mm:.1f}mm deep"
            else:
                feat_type = "through_hole"
                desc = f"Through hole: {hole.diameter_mm:.1f}mm dia"

            features.append(Feature(
                feature_type=feat_type,
                description=desc,
                face_indices=[hole.face_index],
                edge_indices=[],
                dimensions={
                    "diameter_mm": hole.diameter_mm,
                    "depth_mm": hole.depth_mm,
                },
            ))

        # Classify walls
        for wall in walls:
            features.append(Feature(
                feature_type="wall",
                description=f"Wall: {wall.thickness_mm:.1f}mm thick",
                face_indices=[wall.face_index_1, wall.face_index_2],
                edge_indices=[],
                dimensions={"thickness_mm": wall.thickness_mm},
            ))

        # Identify filleted edges
        for edge in edges:
            if edge.edge_type in ("arc", "circle") and edge.radius_mm > 0:
                features.append(Feature(
                    feature_type="fillet",
                    description=f"Fillet: {edge.radius_mm:.1f}mm radius",
                    face_indices=[],
                    edge_indices=[edge.index],
                    dimensions={"radius_mm": edge.radius_mm},
                ))

        return features
