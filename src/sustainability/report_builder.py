"""Facade that composes waste, carbon, and green score into a full report."""

import logging
from typing import Optional

from src.models.sustainability import SustainabilityReport, AISustainabilityReport
from src.sustainability.waste_calculator import WasteCalculator
from src.sustainability.carbon_estimator import CarbonEstimator
from src.sustainability.green_score import GreenScorer
from src.sustainability.ai_scorer import AISustainabilityScorer

logger = logging.getLogger(__name__)


class SustainabilityReportBuilder:
    """Builds a complete sustainability report for a part."""

    def __init__(self):
        self.waste_calc = WasteCalculator()
        self.carbon_est = CarbonEstimator()
        self.green_scorer = GreenScorer()
        self.ai_scorer = AISustainabilityScorer()

    def build(self, volume_cm3: float, bounding_box: dict | None = None) -> SustainabilityReport:
        """Build full sustainability report from part geometry (formula-based, instant)."""
        waste = self.waste_calc.estimate_all(volume_cm3, bounding_box)
        carbon = self.carbon_est.estimate_all(volume_cm3)
        scores = self.green_scorer.score_all(waste, carbon)
        greenest = self.green_scorer.get_greenest(scores)
        recommendation = self.green_scorer.build_recommendation(scores)
        tips = self.green_scorer.build_savings_tips(waste, carbon, scores)

        return SustainabilityReport(
            waste_estimates=waste,
            carbon_estimates=carbon,
            green_scores=scores,
            greenest_process=greenest,
            recommendation=recommendation,
            savings_tips=tips,
        )

    async def build_ai_report(
        self, volume_cm3: float, bounding_box: dict | None = None
    ) -> Optional[AISustainabilityReport]:
        """Run Dedalus AI agent swarm for enriched sustainability scoring.

        Returns None if Dedalus fails (caller should keep formula-based fallback).
        """
        try:
            waste = self.waste_calc.estimate_all(volume_cm3, bounding_box)
            carbon = self.carbon_est.estimate_all(volume_cm3)

            part_info = {
                "volume_cm3": round(volume_cm3, 4),
                "bounding_box": bounding_box or {},
            }

            return await self.ai_scorer.score(waste, carbon, part_info)

        except Exception as e:
            logger.error(f"AI sustainability scoring failed: {e}")
            return None
