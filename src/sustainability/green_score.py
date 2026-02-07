"""Green score calculation: 1-100 sustainability rating per process."""

from src.models.sustainability import WasteEstimate, CarbonEstimate, GreenScore

# Carbon equivalencies for relatable context (kg CO2, description)
CARBON_EQUIVALENCIES = [
    (0.008, "charging a smartphone"),
    (0.036, "streaming video for 1 hour"),
    (0.077, "boiling a kettle"),
    (0.41, "driving 1 mile"),
    (2.3, "a gallon of gasoline burned"),
]

# Recyclability points (0-20) per process default material
RECYCLABILITY_SCORES = {
    "FDM": 15,              # PLA is compostable, moderately recyclable
    "SLA": 5,               # Cured resin is not easily recyclable
    "CNC": 20,              # Aluminum is highly recyclable
    "Injection Molding": 12, # ABS is recyclable but rarely done
}


class GreenScorer:
    """Calculates green sustainability scores for each process."""

    def score_all(
        self,
        waste_estimates: list[WasteEstimate],
        carbon_estimates: list[CarbonEstimate],
    ) -> list[GreenScore]:
        """Score all processes. Returns sorted by score descending."""
        waste_map = {w.process: w for w in waste_estimates}
        carbon_map = {c.process: c for c in carbon_estimates}
        max_carbon = max((c.carbon_kg for c in carbon_estimates), default=1.0) or 1.0

        scores = []
        for process in ["FDM", "SLA", "CNC", "Injection Molding"]:
            w = waste_map.get(process)
            c = carbon_map.get(process)
            if not w or not c:
                continue

            # Waste score: 0-40 pts (lower waste% = higher score)
            waste_pts = max(0.0, 40.0 - w.waste_percent)

            # Carbon score: 0-40 pts (normalized against worst process)
            carbon_pts = 40.0 * (1.0 - c.carbon_kg / max_carbon) if max_carbon > 0 else 0.0

            # Recyclability: 0-20 pts (static per-process)
            recycle_pts = RECYCLABILITY_SCORES.get(process, 10)

            total = int(round(waste_pts + carbon_pts + recycle_pts))
            total = max(1, min(100, total))

            scores.append(GreenScore(
                process=process,
                score=total,
                grade=self._grade(total),
                waste_score=round(waste_pts, 1),
                carbon_score=round(carbon_pts, 1),
                recyclability_score=float(recycle_pts),
                explanation=self._explain(process, waste_pts, carbon_pts, recycle_pts),
            ))

        scores.sort(key=lambda s: s.score, reverse=True)
        return scores

    def get_greenest(self, scores: list[GreenScore]) -> str:
        """Return the process name with highest green score."""
        if not scores:
            return "FDM"
        return max(scores, key=lambda s: s.score).process

    def build_recommendation(self, scores: list[GreenScore]) -> str:
        """Human-readable recommendation for the greenest option."""
        if not scores:
            return "Run analysis first."
        best = max(scores, key=lambda s: s.score)
        return (
            f"{best.process} is the greenest option with a score of {best.score}/100 "
            f"(Grade {best.grade}). {best.explanation}"
        )

    def build_savings_tips(
        self,
        waste_estimates: list[WasteEstimate],
        carbon_estimates: list[CarbonEstimate],
        scores: list[GreenScore],
    ) -> list[dict]:
        """Generate 'if you switch from X to Y, you save Z' messages."""
        if not scores:
            return []

        greenest = max(scores, key=lambda s: s.score)
        waste_map = {w.process: w for w in waste_estimates}
        carbon_map = {c.process: c for c in carbon_estimates}

        tips = []
        for s in scores:
            if s.process == greenest.process:
                continue
            w_from = waste_map.get(s.process)
            w_to = waste_map.get(greenest.process)
            c_from = carbon_map.get(s.process)
            c_to = carbon_map.get(greenest.process)
            if not all([w_from, w_to, c_from, c_to]):
                continue

            waste_saved = w_from.waste_grams - w_to.waste_grams
            carbon_saved = c_from.carbon_kg - c_to.carbon_kg
            tips.append({
                "from": s.process,
                "to": greenest.process,
                "waste_saved_grams": round(waste_saved, 1),
                "carbon_saved_kg": round(carbon_saved, 3),
                "carbon_equivalency": self._carbon_equivalency(abs(carbon_saved)),
                "message": (
                    f"Switching from {s.process} to {greenest.process} "
                    f"saves {abs(waste_saved):.1f}g of waste "
                    f"and {abs(carbon_saved):.3f} kg CO\u2082."
                ),
            })
        return tips

    @staticmethod
    def _carbon_equivalency(carbon_kg: float) -> str:
        """Convert carbon kg to a relatable everyday comparison."""
        if carbon_kg < 0.001:
            return ""
        for threshold, desc in CARBON_EQUIVALENCIES:
            if carbon_kg <= threshold * 2:
                count = carbon_kg / threshold
                if count < 0.1:
                    continue
                if count <= 1.2:
                    return f"~ {desc}"
                return f"~ {count:.1f}x {desc}"
        return f"~ driving {carbon_kg / 0.41:.1f} miles"

    @staticmethod
    def _grade(score: int) -> str:
        """Convert numeric score to letter grade."""
        if score >= 80:
            return "A"
        if score >= 65:
            return "B"
        if score >= 50:
            return "C"
        if score >= 35:
            return "D"
        return "F"

    @staticmethod
    def _explain(process: str, waste_pts: float, carbon_pts: float, recycle_pts: float) -> str:
        """Generate human-readable explanation of the score components."""
        parts = []
        if waste_pts >= 30:
            parts.append("very low waste")
        elif waste_pts >= 15:
            parts.append("moderate waste")
        else:
            parts.append("high material waste")

        if carbon_pts >= 30:
            parts.append("low carbon footprint")
        elif carbon_pts >= 15:
            parts.append("moderate carbon footprint")
        else:
            parts.append("high carbon footprint")

        if recycle_pts >= 15:
            parts.append("highly recyclable material")
        elif recycle_pts >= 10:
            parts.append("moderately recyclable")
        else:
            parts.append("difficult to recycle")

        return f"{', '.join(p.capitalize() for p in parts)}."
