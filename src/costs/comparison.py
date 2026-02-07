"""Multi-process cost comparison with breakeven analysis."""

import logging
from typing import Optional

from src.models.costs import CostComparison, CostBreakdown, CostEstimate
from src.costs.estimator import CostEstimator
from src.costs.quantity_curves import QuantityCurveCalculator

logger = logging.getLogger(__name__)


class CostComparer:
    """Side-by-side cost comparison across manufacturing processes."""

    def __init__(
        self,
        estimator: Optional[CostEstimator] = None,
        curve_calc: Optional[QuantityCurveCalculator] = None,
    ):
        self.estimator = estimator or CostEstimator()
        self.curve_calc = curve_calc or QuantityCurveCalculator(self.estimator)

    def compare(
        self,
        volume_cm3: float,
        area_cm2: float,
        bounding_box: dict | None = None,
        face_count: int = 0,
        quantity: int = 1,
    ) -> CostComparison:
        """Full cost comparison: breakdowns + crossovers + recommendation."""
        bb = bounding_box or {}

        # Get cost curves at standard quantities
        breakdowns = self.curve_calc.calculate_curves(
            volume_cm3, area_cm2, bb, face_count
        )

        # Find crossover points
        crossovers = self.curve_calc.find_crossover_points(
            volume_cm3, area_cm2, bb, face_count
        )

        # Get recommendation for the requested quantity
        estimates = self.estimator.estimate_all(
            volume_cm3, area_cm2, bb, face_count, quantity
        )
        recommendation = self._build_recommendation(estimates, quantity, crossovers)

        return CostComparison(
            breakdowns=breakdowns,
            recommendation=recommendation,
            crossover_points=crossovers,
        )

    def compare_quick(
        self,
        volume_cm3: float,
        area_cm2: float,
        bounding_box: dict | None = None,
        face_count: int = 0,
        quantity: int = 1,
    ) -> list[CostEstimate]:
        """Quick comparison: just the estimates at one quantity, no curves."""
        return self.estimator.estimate_all(
            volume_cm3, area_cm2, bounding_box, face_count, quantity
        )

    def _build_recommendation(
        self,
        estimates: list[CostEstimate],
        quantity: int,
        crossovers: list[dict],
    ) -> str:
        """Build a human-readable recommendation string."""
        if not estimates:
            return "Unable to estimate costs."

        sorted_est = sorted(estimates, key=lambda e: e.total_cost)
        cheapest = sorted_est[0]
        unit_cost = cheapest.total_cost / max(quantity, 1)

        parts = [
            f"At {quantity} unit{'s' if quantity != 1 else ''}, "
            f"{cheapest.process} is cheapest at ${unit_cost:.2f}/unit "
            f"(${cheapest.total_cost:.2f} total)."
        ]

        # Add crossover hints
        for cp in crossovers:
            if cp["quantity"] > quantity:
                parts.append(
                    f" Note: {cp['to']} becomes cheaper above {cp['quantity']} units."
                )
                break  # Only show the nearest upcoming crossover

        return "".join(parts)
