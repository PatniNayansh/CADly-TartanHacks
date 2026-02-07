"""Material matcher — ranks materials by fit for part requirements."""

import logging
from src.models.materials import Material
from src.recommend.material_db import MaterialDB

logger = logging.getLogger(__name__)


class MaterialMatcher:
    """Match part requirements to the best materials."""

    def __init__(self, db: MaterialDB | None = None):
        self.db = db or MaterialDB()

    def match(
        self,
        process: str,
        requirements: dict | None = None,
    ) -> list[dict]:
        """Rank materials for a process + optional requirements.

        Args:
            process: Target process ('fdm', 'sla', 'cnc', 'injection_molding')
            requirements: Optional dict with desired property weights, e.g.
                {'strength': 0.3, 'heat_resistance': 0.2, 'flexibility': 0.1,
                 'cost': 0.2, 'machinability': 0.2}

        Returns:
            List of dicts with material data + spider chart + score, sorted best-first.
        """
        if requirements is None:
            requirements = {
                "strength": 0.25,
                "heat_resistance": 0.2,
                "flexibility": 0.1,
                "cost": 0.25,
                "machinability": 0.2,
            }

        candidates = self.db.filter_by_process(process)
        if not candidates:
            return []

        results = []
        for material in candidates:
            entry = self._score_material(material, requirements)
            results.append(entry)

        results.sort(key=lambda r: r["score"], reverse=True)
        return results

    def _score_material(self, material: Material, requirements: dict) -> dict:
        """Score a single material against requirements."""
        spider = material.properties.spider_chart_data()

        # Weighted score from spider chart values (each 0-10) and requirement weights
        score = sum(
            spider.get(axis, 0) * weight
            for axis, weight in requirements.items()
        )

        # Highlight top properties
        highlights = []
        sorted_axes = sorted(spider.items(), key=lambda kv: kv[1], reverse=True)
        for axis, val in sorted_axes[:2]:
            label = axis.replace("_", " ").title()
            if val >= 7:
                highlights.append(f"Excellent {label}")
            elif val >= 5:
                highlights.append(f"Good {label}")

        return {
            "material": material.to_dict(),
            "score": round(score, 1),
            "spider_chart": spider,
            "highlights": highlights,
        }
