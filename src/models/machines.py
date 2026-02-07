"""Machine data models for the recommendation engine."""

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class BuildVolume:
    """Machine build volume in millimeters."""
    x: float
    y: float
    z: float

    def can_fit(self, part_x: float, part_y: float, part_z: float) -> bool:
        """Check if a part fits within this build volume."""
        dims = sorted([part_x, part_y, part_z])
        vol = sorted([self.x, self.y, self.z])
        return all(d <= v for d, v in zip(dims, vol))


@dataclass
class Machine:
    """A manufacturing machine with specifications."""
    id: str
    name: str
    manufacturer: str
    machine_type: str  # "FDM", "SLA", "CNC"
    build_volume: BuildVolume
    tolerance_mm: float
    materials: list[str]
    price_usd: float
    speed_rating: int  # 1-10
    precision_rating: int  # 1-10
    axes: Optional[int] = None  # 3 or 5 for CNC
    layer_height_range: Optional[list[float]] = None  # For FDM/SLA [min, max] mm
    nozzle_sizes: Optional[list[float]] = None  # For FDM
    limitations: list[str] = field(default_factory=list)
    best_for: list[str] = field(default_factory=list)

    def supports_material(self, material: str) -> bool:
        """Check if this machine supports a given material."""
        return material.upper() in [m.upper() for m in self.materials]

    @classmethod
    def from_dict(cls, data: dict) -> "Machine":
        """Parse from JSON dict."""
        bv = data["build_volume"]
        return cls(
            id=data["id"],
            name=data["name"],
            manufacturer=data["manufacturer"],
            machine_type=data["type"],
            build_volume=BuildVolume(x=bv["x"], y=bv["y"], z=bv["z"]),
            tolerance_mm=data["tolerance_mm"],
            materials=data["materials"],
            price_usd=data["price_usd"],
            speed_rating=data["speed_rating"],
            precision_rating=data["precision_rating"],
            axes=data.get("axes"),
            layer_height_range=data.get("layer_height_range"),
            nozzle_sizes=data.get("nozzle_sizes"),
            limitations=data.get("limitations", []),
            best_for=data.get("best_for", []),
        )

    def to_dict(self) -> dict:
        """Serialize for API response."""
        result = {
            "id": self.id,
            "name": self.name,
            "manufacturer": self.manufacturer,
            "type": self.machine_type,
            "build_volume": {"x": self.build_volume.x, "y": self.build_volume.y, "z": self.build_volume.z},
            "tolerance_mm": self.tolerance_mm,
            "materials": self.materials,
            "price_usd": self.price_usd,
            "speed_rating": self.speed_rating,
            "precision_rating": self.precision_rating,
            "limitations": self.limitations,
            "best_for": self.best_for,
        }
        if self.axes is not None:
            result["axes"] = self.axes
        if self.layer_height_range is not None:
            result["layer_height_range"] = self.layer_height_range
        if self.nozzle_sizes is not None:
            result["nozzle_sizes"] = self.nozzle_sizes
        return result
