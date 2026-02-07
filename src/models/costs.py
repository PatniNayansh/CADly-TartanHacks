"""Cost estimation data models."""

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class CostEstimate:
    """Cost estimate for a single manufacturing process at a given quantity."""
    process: str
    material_cost: float
    machine_time_hrs: float
    time_cost: float
    setup_cost: float
    total_cost: float
    quantity: int = 1

    def to_dict(self) -> dict:
        """Serialize to JSON-compatible dict."""
        return {
            "process": self.process,
            "material_cost": round(self.material_cost, 2),
            "machine_time_hrs": round(self.machine_time_hrs, 2),
            "time_cost": round(self.time_cost, 2),
            "setup_cost": round(self.setup_cost, 2),
            "total_cost": round(self.total_cost, 2),
            "unit_cost": round(self.total_cost / max(self.quantity, 1), 2),
            "quantity": self.quantity,
        }


@dataclass
class CostBreakdown:
    """Detailed cost breakdown for a process at multiple quantities."""
    process: str
    estimates: list[CostEstimate]

    def at_quantity(self, qty: int) -> Optional[CostEstimate]:
        """Find the estimate closest to the given quantity."""
        if not self.estimates:
            return None
        return min(self.estimates, key=lambda e: abs(e.quantity - qty))


@dataclass
class QuantityPoint:
    """A single point on a cost-vs-quantity curve."""
    quantity: int
    unit_cost: float
    total_cost: float


@dataclass
class CostComparison:
    """Multi-process cost comparison with crossover analysis."""
    breakdowns: list[CostBreakdown]
    recommendation: str
    crossover_points: list[dict] = field(default_factory=list)
    # e.g. [{"quantity": 500, "from": "FDM", "to": "CNC", "message": "CNC becomes cheaper above 500 units"}]

    def to_dict(self) -> dict:
        """Serialize for API response."""
        return {
            "processes": [
                {
                    "process": bd.process,
                    "estimates": [e.to_dict() for e in bd.estimates],
                }
                for bd in self.breakdowns
            ],
            "recommendation": self.recommendation,
            "crossover_points": self.crossover_points,
        }
