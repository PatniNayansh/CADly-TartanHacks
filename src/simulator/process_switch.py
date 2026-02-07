"""Core process switching logic — re-analyze geometry for a different process."""

import logging
from dataclasses import dataclass, field

from src.fusion.client import FusionClient
from src.fusion.geometry import GeometryHelper
from src.dfm.engine import DFMEngine
from src.models.violations import Violation, ViolationReport
from src.models.geometry import Body, Face, Edge, Wall, Hole
from src.costs.estimator import CostEstimator
from src.models.costs import CostEstimate

logger = logging.getLogger(__name__)


@dataclass
class ProcessSwitchResult:
    """Result of simulating a process switch."""
    from_process: str
    to_process: str
    removed_violations: list[dict]  # Violations that no longer apply
    new_violations: list[dict]  # Newly introduced violations
    persistent_violations: list[dict]  # Still there in both
    cost_before: dict
    cost_after: dict
    cost_delta: float  # Positive = more expensive, negative = cheaper
    redesign_steps: list[dict]
    summary: str

    def to_dict(self) -> dict:
        return {
            "from_process": self.from_process,
            "to_process": self.to_process,
            "removed_violations": self.removed_violations,
            "new_violations": self.new_violations,
            "persistent_violations": self.persistent_violations,
            "cost_before": self.cost_before,
            "cost_after": self.cost_after,
            "cost_delta": round(self.cost_delta, 2),
            "redesign_steps": self.redesign_steps,
            "summary": self.summary,
        }


class ProcessSwitcher:
    """Simulate switching from one manufacturing process to another."""

    def __init__(self, client: FusionClient):
        self.client = client
        self.engine = DFMEngine(client)
        self.geometry = GeometryHelper(client)
        self.estimator = CostEstimator()

    async def simulate(self, from_process: str, to_process: str) -> ProcessSwitchResult:
        """Run both analyses and diff the results."""
        # Fetch geometry once
        geo_data = await self.geometry.get_all()
        body = geo_data["body"]
        faces = geo_data["faces"]
        edges = geo_data["edges"]
        walls = geo_data["walls"]
        holes = geo_data["holes"]

        # Analyze for both processes
        report_from = self.engine.analyze_with_data(body, faces, edges, walls, holes, from_process)
        report_to = self.engine.analyze_with_data(body, faces, edges, walls, holes, to_process)

        # Diff violations
        from_ids = {(v.rule_id, v.feature_id) for v in report_from.violations}
        to_ids = {(v.rule_id, v.feature_id) for v in report_to.violations}

        removed = [v.to_dict() for v in report_from.violations if (v.rule_id, v.feature_id) not in to_ids]
        new = [v.to_dict() for v in report_to.violations if (v.rule_id, v.feature_id) not in from_ids]
        persistent = [v.to_dict() for v in report_to.violations if (v.rule_id, v.feature_id) in from_ids]

        # Cost comparison
        bb = body.bounding_box if body else {}
        vol = body.volume_cm3 if body else 0
        area = body.area_cm2 if body else 0
        fc = body.face_count if body else 0

        cost_from = self._estimate_for_process(from_process, vol, area, bb, fc)
        cost_to = self._estimate_for_process(to_process, vol, area, bb, fc)
        delta = cost_to.total_cost - cost_from.total_cost

        # Generate redesign steps from new violations
        from src.simulator.redesign_planner import RedesignPlanner
        planner = RedesignPlanner()
        steps = planner.generate_steps(report_to.violations, to_process)

        # Summary
        summary = self._build_summary(from_process, to_process, removed, new, delta)

        return ProcessSwitchResult(
            from_process=from_process,
            to_process=to_process,
            removed_violations=removed,
            new_violations=new,
            persistent_violations=persistent,
            cost_before=cost_from.to_dict(),
            cost_after=cost_to.to_dict(),
            cost_delta=delta,
            redesign_steps=steps,
            summary=summary,
        )

    def _estimate_for_process(
        self, process: str, vol: float, area: float, bb: dict, fc: int
    ) -> CostEstimate:
        """Get cost estimate for a specific process."""
        p = process.lower()
        if p == "fdm":
            return self.estimator.estimate_fdm(vol)
        elif p == "sla":
            return self.estimator.estimate_sla(vol)
        elif p == "cnc":
            return self.estimator.estimate_cnc(vol, bb or {})
        elif p in ("injection_molding", "im"):
            return self.estimator.estimate_im(vol, fc)
        return self.estimator.estimate_fdm(vol)

    def _build_summary(self, from_p, to_p, removed, new, delta) -> str:
        parts = [f"Switching from {from_p.upper()} to {to_p.upper()}: "]
        if removed:
            parts.append(f"{len(removed)} violation(s) resolved. ")
        if new:
            parts.append(f"{len(new)} new violation(s) introduced. ")
        if not removed and not new:
            parts.append("No change in violations. ")
        if delta < 0:
            parts.append(f"Saves ${abs(delta):.2f} per unit.")
        elif delta > 0:
            parts.append(f"Costs ${delta:.2f} more per unit.")
        else:
            parts.append("Same cost.")
        return "".join(parts)
