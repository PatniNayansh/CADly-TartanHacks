from dataclasses import dataclass, asdict
import math


@dataclass
class CostEstimate:
    process: str
    material_cost: float
    machine_time_hrs: float
    time_cost: float
    setup_cost: float
    total_cost: float

    def to_dict(self) -> dict:
        return {
            "process": self.process,
            "material_cost": round(self.material_cost, 2),
            "machine_time_hrs": round(self.machine_time_hrs, 2),
            "time_cost": round(self.time_cost, 2),
            "setup_cost": round(self.setup_cost, 2),
            "total_cost": round(self.total_cost, 2),
        }


class CostEstimator:
    """Estimate manufacturing costs for FDM, SLA, and CNC."""

    def estimate_all(self, volume_cm3: float, area_cm2: float,
                     bounding_box: dict) -> list[CostEstimate]:
        """Calculate cost estimates for all three manufacturing processes."""
        return [
            self._estimate_fdm(volume_cm3),
            self._estimate_sla(volume_cm3),
            self._estimate_cnc(volume_cm3, bounding_box),
        ]

    def _estimate_fdm(self, volume_cm3: float) -> CostEstimate:
        """FDM: material × $0.05/cm³ + time × $0.50/hr."""
        material_cost = volume_cm3 * 0.05
        # FDM print rate: ~15 cm³/hr (including infill at ~20%)
        time_hrs = volume_cm3 / 15.0
        time_cost = time_hrs * 0.50
        return CostEstimate(
            process="FDM",
            material_cost=material_cost,
            machine_time_hrs=time_hrs,
            time_cost=time_cost,
            setup_cost=0,
            total_cost=material_cost + time_cost,
        )

    def _estimate_sla(self, volume_cm3: float) -> CostEstimate:
        """SLA: material × $0.15/cm³ + time × $1.00/hr."""
        material_cost = volume_cm3 * 0.15
        # SLA print rate: ~30 cm³/hr (layer-based, faster for flat parts)
        time_hrs = volume_cm3 / 30.0
        time_cost = time_hrs * 1.00
        return CostEstimate(
            process="SLA",
            material_cost=material_cost,
            machine_time_hrs=time_hrs,
            time_cost=time_cost,
            setup_cost=0,
            total_cost=material_cost + time_cost,
        )

    def _estimate_cnc(self, volume_cm3: float, bounding_box: dict) -> CostEstimate:
        """CNC: time × $80/hr + material + $50 setup."""
        # Stock material = bounding box volume (aluminum block)
        bb_min = bounding_box.get("min", [0, 0, 0])
        bb_max = bounding_box.get("max", [1, 1, 1])
        stock_vol = abs(
            (bb_max[0] - bb_min[0]) *
            (bb_max[1] - bb_min[1]) *
            (bb_max[2] - bb_min[2])
        )
        # Aluminum stock cost ~$0.01/cm³
        material_cost = stock_vol * 0.01
        # Material removal rate: ~50 cm³/hr
        removal_vol = max(0, stock_vol - volume_cm3)
        time_hrs = removal_vol / 50.0
        # Minimum machining time
        time_hrs = max(time_hrs, 0.25)
        time_cost = time_hrs * 80.0
        setup_cost = 50.0
        return CostEstimate(
            process="CNC",
            material_cost=material_cost,
            machine_time_hrs=time_hrs,
            time_cost=time_cost,
            setup_cost=setup_cost,
            total_cost=material_cost + time_cost + setup_cost,
        )

    def get_recommendation(self, estimates: list[CostEstimate]) -> str:
        """Return the cheapest manufacturing process."""
        if not estimates:
            return "FDM"
        cheapest = min(estimates, key=lambda e: e.total_cost)
        return cheapest.process
