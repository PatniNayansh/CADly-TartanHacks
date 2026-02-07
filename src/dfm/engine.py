"""DFM analysis engine.

Main orchestrator that queries Fusion 360 geometry, runs all analysis
modules, applies matching rules, and produces a ViolationReport.
"""

import logging
from typing import Optional

from src.fusion.client import FusionClient
from src.fusion.geometry import GeometryHelper
from src.models.violations import Violation, Severity, ManufacturingProcess, ViolationReport
from src.models.geometry import Body, Face, Edge, Wall, Hole
from src.analysis.walls import WallAnalyzer
from src.analysis.corners import CornerAnalyzer
from src.analysis.holes import HoleAnalyzer
from src.analysis.overhangs import OverhangAnalyzer
from .registry import get_registry
from .rules import DFMRule

logger = logging.getLogger(__name__)


class DFMEngine:
    """Central DFM analysis engine.

    Coordinates geometry extraction and rule evaluation to produce
    a complete violation report for a part.
    """

    def __init__(self, client: FusionClient):
        self.client = client
        self.geometry = GeometryHelper(client)
        self.wall_analyzer = WallAnalyzer()
        self.corner_analyzer = CornerAnalyzer()
        self.hole_analyzer = HoleAnalyzer()
        self.overhang_analyzer = OverhangAnalyzer()

    async def analyze(self, process: str = "all") -> ViolationReport:
        """Run full DFM analysis on the current Fusion 360 part.

        Args:
            process: Target process to check ("all", "fdm", "sla", "cnc", "injection_molding").

        Returns:
            ViolationReport with all detected violations and metadata.
        """
        # Fetch all geometry from Fusion
        try:
            geo_data = await self.geometry.get_all()
        except Exception as e:
            logger.error(f"Failed to query Fusion 360 geometry: {e}")
            return ViolationReport(
                part_name="Error",
                violations=[Violation(
                    rule_id="SYS-001",
                    severity=Severity.CRITICAL,
                    message=f"Cannot connect to Fusion 360: {e}",
                    feature_id="system",
                    current_value=0,
                    required_value=0,
                    fixable=False,
                    process=ManufacturingProcess.FDM,
                )],
                is_manufacturable=False,
            )

        body: Optional[Body] = geo_data["body"]
        faces: list[Face] = geo_data["faces"]
        edges: list[Edge] = geo_data["edges"]
        walls: list[Wall] = geo_data["walls"]
        holes: list[Hole] = geo_data["holes"]

        # Get applicable rules
        registry = get_registry()
        rules = registry.rules_for_process(process)

        # Run all analysis modules
        violations: list[Violation] = []
        violations.extend(self.wall_analyzer.check(walls, rules))
        violations.extend(self.corner_analyzer.check(edges, rules))
        violations.extend(self.hole_analyzer.check(holes, rules, process))
        violations.extend(self.overhang_analyzer.check(faces, rules))

        # Build report
        report = ViolationReport(
            part_name=body.name if body else "Unknown",
            violations=violations,
            is_manufacturable=not any(v.severity == Severity.CRITICAL for v in violations),
            body_volume_cm3=body.volume_cm3 if body else 0,
            body_area_cm2=body.area_cm2 if body else 0,
            bounding_box=body.bounding_box if body else None,
        )

        # Recommend best process
        report.recommended_process = self._recommend_process(violations)

        logger.info(
            f"Analysis complete: {report.violation_count} violations "
            f"({report.critical_count} critical, {report.warning_count} warnings)"
        )

        return report

    def analyze_with_data(
        self,
        body: Optional[Body],
        faces: list[Face],
        edges: list[Edge],
        walls: list[Wall],
        holes: list[Hole],
        process: str = "all",
    ) -> ViolationReport:
        """Run DFM analysis on pre-fetched geometry data.

        Useful for the process switch simulator which needs to re-analyze
        the same geometry with different process rules without re-querying Fusion.
        """
        registry = get_registry()
        rules = registry.rules_for_process(process)

        violations: list[Violation] = []
        violations.extend(self.wall_analyzer.check(walls, rules))
        violations.extend(self.corner_analyzer.check(edges, rules))
        violations.extend(self.hole_analyzer.check(holes, rules, process))
        violations.extend(self.overhang_analyzer.check(faces, rules))

        report = ViolationReport(
            part_name=body.name if body else "Unknown",
            violations=violations,
            is_manufacturable=not any(v.severity == Severity.CRITICAL for v in violations),
            body_volume_cm3=body.volume_cm3 if body else 0,
            body_area_cm2=body.area_cm2 if body else 0,
            bounding_box=body.bounding_box if body else None,
        )
        report.recommended_process = self._recommend_process(violations)
        return report

    def _recommend_process(self, violations: list[Violation]) -> str:
        """Recommend the best manufacturing process based on violation counts.

        Scores each process by its violations (critical=10, warning=3, suggestion=1).
        Lower score = fewer issues = better fit.
        """
        scores = {"FDM": 0, "SLA": 0, "CNC": 0}
        weight = {
            Severity.CRITICAL: 10,
            Severity.WARNING: 3,
            Severity.SUGGESTION: 1,
        }

        for v in violations:
            process_key = v.rule_id.split("-")[0]
            if process_key in scores:
                scores[process_key] += weight.get(v.severity, 1)
            elif process_key == "GEN":
                # General rules penalize all processes slightly
                for key in scores:
                    scores[key] += weight.get(v.severity, 1)

        return min(scores, key=scores.get)
