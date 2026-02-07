"""Sustainability data models for waste, carbon, and green scoring."""

from dataclasses import dataclass, field


@dataclass
class WasteEstimate:
    """Material waste estimate for a single manufacturing process."""
    process: str
    part_volume_cm3: float
    raw_material_cm3: float
    waste_cm3: float
    waste_percent: float
    waste_grams: float
    breakdown: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "process": self.process,
            "part_volume_cm3": round(self.part_volume_cm3, 2),
            "raw_material_cm3": round(self.raw_material_cm3, 2),
            "waste_cm3": round(self.waste_cm3, 2),
            "waste_percent": round(self.waste_percent, 1),
            "waste_grams": round(self.waste_grams, 1),
            "breakdown": self.breakdown,
        }


@dataclass
class CarbonEstimate:
    """Energy and carbon footprint estimate for a single process."""
    process: str
    part_mass_grams: float
    energy_kwh: float
    carbon_kg: float
    kwh_per_gram: float
    carbon_factor: float

    def to_dict(self) -> dict:
        return {
            "process": self.process,
            "part_mass_grams": round(self.part_mass_grams, 1),
            "energy_kwh": round(self.energy_kwh, 3),
            "carbon_kg": round(self.carbon_kg, 3),
            "kwh_per_gram": self.kwh_per_gram,
            "carbon_factor": self.carbon_factor,
        }


@dataclass
class GreenScore:
    """Sustainability score (1-100) for a manufacturing process."""
    process: str
    score: int
    grade: str
    waste_score: float
    carbon_score: float
    recyclability_score: float
    explanation: str

    def to_dict(self) -> dict:
        return {
            "process": self.process,
            "score": self.score,
            "grade": self.grade,
            "waste_score": round(self.waste_score, 1),
            "carbon_score": round(self.carbon_score, 1),
            "recyclability_score": round(self.recyclability_score, 1),
            "explanation": self.explanation,
        }


@dataclass
class SustainabilityReport:
    """Full sustainability report across all processes."""
    waste_estimates: list[WasteEstimate]
    carbon_estimates: list[CarbonEstimate]
    green_scores: list[GreenScore]
    greenest_process: str
    recommendation: str
    savings_tips: list[dict] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "waste": [w.to_dict() for w in self.waste_estimates],
            "carbon": [c.to_dict() for c in self.carbon_estimates],
            "green_scores": [g.to_dict() for g in self.green_scores],
            "greenest_process": self.greenest_process,
            "recommendation": self.recommendation,
            "savings_tips": self.savings_tips,
        }


# ---- AI-Enriched Models (Dedalus Agent Swarm) ----

@dataclass
class AIProcessAnalysis:
    """AI-generated sustainability analysis for a single process."""
    process: str
    score: int
    grade: str
    waste_sub_score: int
    carbon_sub_score: int
    recyclability_sub_score: int
    justification: str
    strengths: list[str] = field(default_factory=list)
    weaknesses: list[str] = field(default_factory=list)
    circular_economy_notes: str = ""
    contextual_comparison: str = ""

    def to_dict(self) -> dict:
        return {
            "process": self.process,
            "score": self.score,
            "grade": self.grade,
            "waste_sub_score": self.waste_sub_score,
            "carbon_sub_score": self.carbon_sub_score,
            "recyclability_sub_score": self.recyclability_sub_score,
            "justification": self.justification,
            "strengths": self.strengths,
            "weaknesses": self.weaknesses,
            "circular_economy_notes": self.circular_economy_notes,
            "contextual_comparison": self.contextual_comparison,
        }


@dataclass
class AITradeOff:
    """Trade-off comparison between two processes."""
    process_a: str
    process_b: str
    winner: str
    summary: str
    environmental_delta: str = ""

    def to_dict(self) -> dict:
        return {
            "process_a": self.process_a,
            "process_b": self.process_b,
            "winner": self.winner,
            "summary": self.summary,
            "environmental_delta": self.environmental_delta,
        }


@dataclass
class AISustainabilityReport:
    """Full AI-enriched sustainability report from the Dedalus agent swarm."""
    process_analyses: list[AIProcessAnalysis]
    overall_recommendation: str
    sustainability_roadmap: list[str]
    trade_offs: list[AITradeOff]
    agent_reasoning: dict
    greenest_process: str
    confidence_note: str = ""
    powered_by: str = "Dedalus Labs"

    def to_dict(self) -> dict:
        return {
            "process_analyses": [a.to_dict() for a in self.process_analyses],
            "overall_recommendation": self.overall_recommendation,
            "sustainability_roadmap": self.sustainability_roadmap,
            "trade_offs": [t.to_dict() for t in self.trade_offs],
            "agent_reasoning": self.agent_reasoning,
            "greenest_process": self.greenest_process,
            "confidence_note": self.confidence_note,
            "powered_by": self.powered_by,
        }
