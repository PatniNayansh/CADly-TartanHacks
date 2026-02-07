"""Material data models for the recommendation engine."""

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class MaterialProperty:
    """Physical and mechanical properties of a material."""
    tensile_strength_mpa: Optional[float] = None
    yield_strength_mpa: Optional[float] = None
    elongation_pct: Optional[float] = None
    density_g_cm3: Optional[float] = None
    heat_deflection_c: Optional[float] = None
    shore_hardness: Optional[str] = None
    cost_per_kg_usd: Optional[float] = None
    machinability_rating: Optional[int] = None  # 1-10

    def to_dict(self) -> dict:
        """Serialize, omitting None values."""
        return {k: v for k, v in {
            "tensile_strength_mpa": self.tensile_strength_mpa,
            "yield_strength_mpa": self.yield_strength_mpa,
            "elongation_pct": self.elongation_pct,
            "density_g_cm3": self.density_g_cm3,
            "heat_deflection_c": self.heat_deflection_c,
            "shore_hardness": self.shore_hardness,
            "cost_per_kg_usd": self.cost_per_kg_usd,
            "machinability_rating": self.machinability_rating,
        }.items() if v is not None}

    def spider_chart_data(self) -> dict[str, float]:
        """Normalized 0-10 scores for spider chart rendering."""
        return {
            "strength": min(10, (self.tensile_strength_mpa or 0) / 100),
            "heat_resistance": min(10, (self.heat_deflection_c or 0) / 30),
            "flexibility": min(10, (self.elongation_pct or 0) / 10),
            "cost": max(0, 10 - (self.cost_per_kg_usd or 0) / 10),
            "machinability": self.machinability_rating or 5,
        }


@dataclass
class Material:
    """A manufacturing material with properties."""
    id: str
    name: str
    category: str  # "thermoplastic", "resin", "metal", "engineering_plastic"
    processes: list[str]  # ["FDM", "CNC", etc.]
    properties: MaterialProperty
    advantages: list[str] = field(default_factory=list)
    disadvantages: list[str] = field(default_factory=list)
    typical_uses: list[str] = field(default_factory=list)

    def supports_process(self, process: str) -> bool:
        """Check if this material works with a given process."""
        return process.upper() in [p.upper() for p in self.processes]

    @classmethod
    def from_dict(cls, data: dict) -> "Material":
        """Parse from JSON dict."""
        props = data.get("properties", {})
        return cls(
            id=data["id"],
            name=data["name"],
            category=data["category"],
            processes=data["processes"],
            properties=MaterialProperty(
                tensile_strength_mpa=props.get("tensile_strength_mpa"),
                yield_strength_mpa=props.get("yield_strength_mpa"),
                elongation_pct=props.get("elongation_pct"),
                density_g_cm3=props.get("density_g_cm3"),
                heat_deflection_c=props.get("heat_deflection_c"),
                shore_hardness=props.get("shore_hardness"),
                cost_per_kg_usd=props.get("cost_per_kg_usd"),
                machinability_rating=props.get("machinability_rating"),
            ),
            advantages=data.get("advantages", []),
            disadvantages=data.get("disadvantages", []),
            typical_uses=data.get("typical_uses", []),
        )

    def to_dict(self) -> dict:
        """Serialize for API response."""
        return {
            "id": self.id,
            "name": self.name,
            "category": self.category,
            "processes": self.processes,
            "properties": self.properties.to_dict(),
            "spider_chart": self.properties.spider_chart_data(),
            "advantages": self.advantages,
            "disadvantages": self.disadvantages,
            "typical_uses": self.typical_uses,
        }
