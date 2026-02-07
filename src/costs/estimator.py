"""Per-process cost estimation for FDM, SLA, CNC, and Injection Molding."""

import math
import logging

from src.models.costs import CostEstimate

logger = logging.getLogger(__name__)

# ---- Cost constants ----

# FDM
FDM_MATERIAL_PER_CM3 = 0.05  # $/cm3 (PLA filament)
FDM_MACHINE_PER_HR = 0.50  # $/hr electricity + depreciation
FDM_PRINT_RATE_CM3_HR = 15.0  # cm3/hr at ~20% infill

# SLA
SLA_MATERIAL_PER_CM3 = 0.15  # $/cm3 (standard resin)
SLA_MACHINE_PER_HR = 1.00  # $/hr
SLA_PRINT_RATE_CM3_HR = 30.0  # cm3/hr (layer-based)

# CNC
CNC_MACHINE_PER_HR = 80.0  # $/hr (3-axis mill)
CNC_SETUP_COST = 50.0  # $ per job
CNC_MATERIAL_PER_CM3 = 0.01  # $/cm3 (aluminum 6061 stock)
CNC_REMOVAL_RATE_CM3_HR = 50.0  # cm3/hr material removal

# Injection Molding
IM_BASE_TOOLING = 5000.0  # $ base mold cost
IM_COMPLEXITY_FACTOR = 500.0  # $ per face (rough complexity proxy)
IM_MAX_TOOLING = 50000.0  # $ cap
IM_MATERIAL_PER_CM3 = 0.02  # $/cm3 (ABS pellets)
IM_CYCLE_TIME_BASE_S = 15.0  # seconds per shot (base)
IM_MACHINE_PER_HR = 40.0  # $/hr machine time


class CostEstimator:
    """Estimate manufacturing costs per process based on part geometry."""

    def estimate_all(
        self,
        volume_cm3: float,
        area_cm2: float,
        bounding_box: dict | None = None,
        face_count: int = 0,
        quantity: int = 1,
    ) -> list[CostEstimate]:
        """Calculate cost estimates for all manufacturing processes."""
        bb = bounding_box or {}
        return [
            self.estimate_fdm(volume_cm3, quantity=quantity),
            self.estimate_sla(volume_cm3, quantity=quantity),
            self.estimate_cnc(volume_cm3, bb, quantity=quantity),
            self.estimate_im(volume_cm3, face_count, quantity=quantity),
        ]

    # ---- FDM ----

    def estimate_fdm(self, volume_cm3: float, quantity: int = 1) -> CostEstimate:
        """FDM: material cost + machine time. Scales linearly with quantity."""
        material_cost = volume_cm3 * FDM_MATERIAL_PER_CM3 * quantity
        time_hrs = (volume_cm3 / FDM_PRINT_RATE_CM3_HR) * quantity
        time_cost = time_hrs * FDM_MACHINE_PER_HR
        return CostEstimate(
            process="FDM",
            material_cost=material_cost,
            machine_time_hrs=time_hrs,
            time_cost=time_cost,
            setup_cost=0.0,
            total_cost=material_cost + time_cost,
            quantity=quantity,
        )

    # ---- SLA ----

    def estimate_sla(self, volume_cm3: float, quantity: int = 1) -> CostEstimate:
        """SLA: resin cost + machine time. Scales linearly with quantity."""
        material_cost = volume_cm3 * SLA_MATERIAL_PER_CM3 * quantity
        time_hrs = (volume_cm3 / SLA_PRINT_RATE_CM3_HR) * quantity
        time_cost = time_hrs * SLA_MACHINE_PER_HR
        return CostEstimate(
            process="SLA",
            material_cost=material_cost,
            machine_time_hrs=time_hrs,
            time_cost=time_cost,
            setup_cost=0.0,
            total_cost=material_cost + time_cost,
            quantity=quantity,
        )

    # ---- CNC ----

    def estimate_cnc(
        self,
        volume_cm3: float,
        bounding_box: dict,
        quantity: int = 1,
    ) -> CostEstimate:
        """CNC: machine time + material + one-time setup cost."""
        stock_vol = self._bounding_box_volume(bounding_box)
        material_cost = stock_vol * CNC_MATERIAL_PER_CM3 * quantity
        removal_vol = max(0.0, stock_vol - volume_cm3)
        time_per_part = max(removal_vol / CNC_REMOVAL_RATE_CM3_HR, 0.25)
        time_hrs = time_per_part * quantity
        time_cost = time_hrs * CNC_MACHINE_PER_HR
        # Setup is one-time regardless of quantity
        setup_cost = CNC_SETUP_COST
        return CostEstimate(
            process="CNC",
            material_cost=material_cost,
            machine_time_hrs=time_hrs,
            time_cost=time_cost,
            setup_cost=setup_cost,
            total_cost=material_cost + time_cost + setup_cost,
            quantity=quantity,
        )

    # ---- Injection Molding ----

    def estimate_im(
        self,
        volume_cm3: float,
        face_count: int = 0,
        quantity: int = 1,
    ) -> CostEstimate:
        """Injection molding: high tooling + low per-unit cost."""
        tooling_cost = min(
            IM_BASE_TOOLING + face_count * IM_COMPLEXITY_FACTOR,
            IM_MAX_TOOLING,
        )
        material_cost = volume_cm3 * IM_MATERIAL_PER_CM3 * quantity
        cycle_s = IM_CYCLE_TIME_BASE_S + volume_cm3 * 0.5
        time_hrs = (cycle_s / 3600.0) * quantity
        time_cost = time_hrs * IM_MACHINE_PER_HR
        # Tooling is one-time, amortized over quantity in unit_cost
        setup_cost = tooling_cost
        return CostEstimate(
            process="Injection Molding",
            material_cost=material_cost,
            machine_time_hrs=time_hrs,
            time_cost=time_cost,
            setup_cost=setup_cost,
            total_cost=material_cost + time_cost + setup_cost,
            quantity=quantity,
        )

    # ---- Helpers ----

    @staticmethod
    def _bounding_box_volume(bb: dict) -> float:
        """Calculate bounding box volume in cm3."""
        bb_min = bb.get("min", [0, 0, 0])
        bb_max = bb.get("max", [1, 1, 1])
        return abs(
            (bb_max[0] - bb_min[0])
            * (bb_max[1] - bb_min[1])
            * (bb_max[2] - bb_min[2])
        )

    @staticmethod
    def get_recommendation(estimates: list[CostEstimate]) -> str:
        """Return the cheapest process name."""
        if not estimates:
            return "FDM"
        cheapest = min(estimates, key=lambda e: e.total_cost)
        return cheapest.process
