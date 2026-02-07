"""Typed geometry data models parsed from Fusion 360 HTTP responses."""

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class Face:
    """A face on a body in Fusion 360."""
    index: int
    face_type: str  # "plane", "cylinder", "cone", "sphere", "torus"
    area_cm2: float
    normal: Optional[list[float]] = None  # For planar faces [x, y, z]
    radius_cm: Optional[float] = None  # For cylindrical/spherical faces
    centroid: Optional[list[float]] = None

    @classmethod
    def from_dict(cls, data: dict) -> "Face":
        """Parse from Fusion HTTP response dict."""
        return cls(
            index=data["index"],
            face_type=data.get("type", "unknown"),
            area_cm2=data.get("area_cm2", 0.0),
            normal=data.get("normal"),
            radius_cm=data.get("radius_cm"),
            centroid=data.get("centroid"),
        )


@dataclass
class Edge:
    """An edge on a body in Fusion 360."""
    index: int
    edge_type: str  # "line", "circle", "arc"
    length_cm: float
    radius_cm: Optional[float] = None
    start: Optional[list[float]] = None
    end: Optional[list[float]] = None
    angle_deg: Optional[float] = None
    is_concave: bool = False

    @property
    def radius_mm(self) -> float:
        """Edge radius in millimeters."""
        return (self.radius_cm or 0.0) * 10.0

    @classmethod
    def from_dict(cls, data: dict) -> "Edge":
        """Parse from Fusion HTTP response dict."""
        return cls(
            index=data["index"],
            edge_type=data.get("type", "unknown"),
            length_cm=data.get("length_cm", 0.0),
            radius_cm=data.get("radius_cm"),
            start=data.get("start"),
            end=data.get("end"),
            angle_deg=data.get("angle_deg"),
            is_concave=data.get("is_concave", False),
        )


@dataclass
class Body:
    """A solid body in Fusion 360."""
    name: str
    volume_cm3: float
    area_cm2: float
    face_count: int
    edge_count: int
    bounding_box: Optional[dict] = None  # {"min": [x,y,z], "max": [x,y,z]}

    @property
    def volume_mm3(self) -> float:
        """Volume in cubic millimeters."""
        return self.volume_cm3 * 1000.0

    @classmethod
    def from_dict(cls, data: dict) -> "Body":
        """Parse from Fusion HTTP response dict."""
        return cls(
            name=data.get("name", "Unknown"),
            volume_cm3=data.get("volume_cm3", 0.0),
            area_cm2=data.get("area_cm2", 0.0),
            face_count=data.get("face_count", 0),
            edge_count=data.get("edge_count", 0),
            bounding_box=data.get("bounding_box"),
        )


@dataclass
class Wall:
    """A wall (pair of parallel faces) detected in the part."""
    face_index_1: int
    face_index_2: int
    thickness_mm: float
    centroid: Optional[list[float]] = None

    @classmethod
    def from_dict(cls, data: dict) -> "Wall":
        """Parse from Fusion HTTP response dict."""
        return cls(
            face_index_1=data["face_index_1"],
            face_index_2=data["face_index_2"],
            thickness_mm=data["thickness_mm"],
            centroid=data.get("centroid"),
        )


@dataclass
class Hole:
    """A cylindrical hole detected in the part."""
    face_index: int
    diameter_mm: float
    depth_mm: float
    depth_to_diameter_ratio: float
    centroid: Optional[list[float]] = None

    @classmethod
    def from_dict(cls, data: dict) -> "Hole":
        """Parse from Fusion HTTP response dict."""
        return cls(
            face_index=data["face_index"],
            diameter_mm=data["diameter_mm"],
            depth_mm=data["depth_mm"],
            depth_to_diameter_ratio=data.get("depth_to_diameter_ratio", 0.0),
            centroid=data.get("centroid"),
        )


@dataclass
class Corner:
    """An internal corner (concave edge) detected in the part."""
    edge_index: int
    radius_mm: float
    edge_type: str  # "line" (sharp) or "arc" (filleted)
    location: Optional[list[float]] = None

    @property
    def is_sharp(self) -> bool:
        """True if the corner has no fillet (radius ~0)."""
        return self.radius_mm < 0.01
