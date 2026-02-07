"""Cost-vs-quantity modeling with crossover detection."""

import logging
from typing import Optional

from src.models.costs import CostEstimate, CostBreakdown, QuantityPoint
from src.costs.estimator import CostEstimator

logger = logging.getLogger(__name__)

# Standard quantity points for curve generation
STANDARD_QUANTITIES = [1, 10, 50, 100, 500, 1000, 5000, 10000]

PROCESSES = ["FDM", "SLA", "CNC", "Injection Molding"]


class QuantityCurveCalculator:
    """Generate cost-vs-quantity curves for each manufacturing process."""

    def __init__(self, estimator: Optional[CostEstimator] = None):
        self.estimator = estimator or CostEstimator()

    def calculate_curves(
        self,
        volume_cm3: float,
        area_cm2: float,
        bounding_box: dict | None = None,
        face_count: int = 0,
        quantities: list[int] | None = None,
    ) -> list[CostBreakdown]:
        """Generate cost breakdowns at multiple quantities for all processes."""
        qtys = quantities or STANDARD_QUANTITIES
        bb = bounding_box or {}
        breakdowns = []

        for process in PROCESSES:
            estimates = []
            for qty in qtys:
                est = self._estimate_for(process, volume_cm3, bb, face_count, qty)
                estimates.append(est)
            breakdowns.append(CostBreakdown(process=process, estimates=estimates))

        return breakdowns

    def get_quantity_points(
        self,
        volume_cm3: float,
        area_cm2: float,
        bounding_box: dict | None = None,
        face_count: int = 0,
        quantities: list[int] | None = None,
    ) -> dict[str, list[QuantityPoint]]:
        """Get unit-cost points for chart rendering. Returns {process: [points]}."""
        qtys = quantities or STANDARD_QUANTITIES
        bb = bounding_box or {}
        result: dict[str, list[QuantityPoint]] = {}

        for process in PROCESSES:
            points = []
            for qty in qtys:
                est = self._estimate_for(process, volume_cm3, bb, face_count, qty)
                unit_cost = est.total_cost / max(qty, 1)
                points.append(QuantityPoint(
                    quantity=qty,
                    unit_cost=round(unit_cost, 4),
                    total_cost=round(est.total_cost, 2),
                ))
            result[process] = points

        return result

    def find_crossover_points(
        self,
        volume_cm3: float,
        area_cm2: float,
        bounding_box: dict | None = None,
        face_count: int = 0,
    ) -> list[dict]:
        """Find quantities where one process becomes cheaper than another."""
        bb = bounding_box or {}
        crossovers = []

        # Check every pair of processes
        for i, proc_a in enumerate(PROCESSES):
            for proc_b in PROCESSES[i + 1 :]:
                cp = self._find_crossover_pair(
                    proc_a, proc_b, volume_cm3, bb, face_count
                )
                if cp:
                    crossovers.append(cp)

        crossovers.sort(key=lambda c: c["quantity"])
        return crossovers

    def _find_crossover_pair(
        self,
        proc_a: str,
        proc_b: str,
        volume_cm3: float,
        bounding_box: dict,
        face_count: int,
    ) -> dict | None:
        """Binary search for crossover quantity between two processes."""
        # Check unit costs at extremes
        cost_a_1 = self._unit_cost(proc_a, volume_cm3, bounding_box, face_count, 1)
        cost_b_1 = self._unit_cost(proc_b, volume_cm3, bounding_box, face_count, 1)
        cost_a_max = self._unit_cost(proc_a, volume_cm3, bounding_box, face_count, 10000)
        cost_b_max = self._unit_cost(proc_b, volume_cm3, bounding_box, face_count, 10000)

        # Check if A is cheaper at low qty and B at high (or vice versa)
        a_cheaper_at_1 = cost_a_1 < cost_b_1
        a_cheaper_at_max = cost_a_max < cost_b_max

        if a_cheaper_at_1 == a_cheaper_at_max:
            return None  # No crossover in range

        # Binary search between 1 and 10000
        lo, hi = 1, 10000
        while hi - lo > 1:
            mid = (lo + hi) // 2
            ca = self._unit_cost(proc_a, volume_cm3, bounding_box, face_count, mid)
            cb = self._unit_cost(proc_b, volume_cm3, bounding_box, face_count, mid)
            if (ca < cb) == a_cheaper_at_1:
                lo = mid
            else:
                hi = mid

        cheaper_first = proc_a if a_cheaper_at_1 else proc_b
        cheaper_after = proc_b if a_cheaper_at_1 else proc_a

        return {
            "quantity": hi,
            "from": cheaper_first,
            "to": cheaper_after,
            "message": f"{cheaper_after} becomes cheaper than {cheaper_first} above {hi} units",
        }

    def _unit_cost(
        self,
        process: str,
        volume_cm3: float,
        bounding_box: dict,
        face_count: int,
        quantity: int,
    ) -> float:
        """Get unit cost for a process at a given quantity."""
        est = self._estimate_for(process, volume_cm3, bounding_box, face_count, quantity)
        return est.total_cost / max(quantity, 1)

    def _estimate_for(
        self,
        process: str,
        volume_cm3: float,
        bounding_box: dict,
        face_count: int,
        quantity: int,
    ) -> CostEstimate:
        """Get estimate for a specific process and quantity."""
        if process == "FDM":
            return self.estimator.estimate_fdm(volume_cm3, quantity=quantity)
        elif process == "SLA":
            return self.estimator.estimate_sla(volume_cm3, quantity=quantity)
        elif process == "CNC":
            return self.estimator.estimate_cnc(volume_cm3, bounding_box, quantity=quantity)
        elif process == "Injection Molding":
            return self.estimator.estimate_im(volume_cm3, face_count, quantity=quantity)
        else:
            raise ValueError(f"Unknown process: {process}")
