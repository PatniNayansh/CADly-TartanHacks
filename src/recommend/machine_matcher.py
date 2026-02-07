"""Machine matcher — ranks machines by fit for a given part."""

import logging
from src.models.machines import Machine
from src.recommend.machine_db import MachineDB, PROCESS_MAP

logger = logging.getLogger(__name__)


class MachineMatcher:
    """Match a part to the best machines from the database."""

    def __init__(self, db: MachineDB | None = None):
        self.db = db or MachineDB()

    def match(
        self,
        process: str,
        bounding_box: dict | None = None,
        volume_cm3: float = 0,
        tolerance_needed_mm: float | None = None,
        priorities: dict | None = None,
    ) -> list[dict]:
        """Rank machines for a part.

        Args:
            process: Target process ('fdm', 'sla', 'cnc', 'injection_molding')
            bounding_box: Part bounding box {'x': mm, 'y': mm, 'z': mm}
            volume_cm3: Part volume (used for IM weight estimate)
            tolerance_needed_mm: Required tolerance (optional, for scoring)
            priorities: Weight dict e.g. {'speed': 0.3, 'precision': 0.4, 'cost': 0.3}

        Returns:
            List of dicts with machine data + score + reasons, sorted best-first.
        """
        if priorities is None:
            priorities = {"speed": 0.3, "precision": 0.4, "cost": 0.3}

        # Step 1: Filter by process
        candidates = self.db.filter_by_process(process)
        if not candidates:
            return []

        # Step 2: Check fit and build results
        results = []
        for machine in candidates:
            entry = self._score_machine(machine, bounding_box, volume_cm3, tolerance_needed_mm, priorities)
            results.append(entry)

        # Sort: fits_part first, then by score descending
        results.sort(key=lambda r: (r["fits_part"], r["score"]), reverse=True)
        return results

    def _score_machine(
        self,
        machine: Machine,
        bounding_box: dict | None,
        volume_cm3: float,
        tolerance_needed_mm: float | None,
        priorities: dict,
    ) -> dict:
        """Score a single machine for the given part."""
        fits = True
        reasons = []
        warnings = []

        # Check build volume fit
        if bounding_box:
            px = bounding_box.get("x", 0)
            py = bounding_box.get("y", 0)
            pz = bounding_box.get("z", 0)
            if machine.build_volume.can_fit(px, py, pz):
                headroom = min(
                    (machine.build_volume.x - px) / machine.build_volume.x,
                    (machine.build_volume.y - py) / machine.build_volume.y,
                    (machine.build_volume.z - pz) / machine.build_volume.z,
                )
                if headroom > 0.5:
                    reasons.append("Part fits easily with lots of headroom")
                else:
                    reasons.append("Part fits within build volume")
            else:
                fits = False
                warnings.append(
                    f"Part ({px:.0f}x{py:.0f}x{pz:.0f}mm) exceeds build volume "
                    f"({machine.build_volume.x:.0f}x{machine.build_volume.y:.0f}x{machine.build_volume.z:.0f}mm)"
                )

        # Tolerance check
        if tolerance_needed_mm is not None:
            if machine.tolerance_mm <= tolerance_needed_mm:
                reasons.append(f"Meets tolerance requirement ({machine.tolerance_mm}mm <= {tolerance_needed_mm}mm)")
            else:
                warnings.append(f"Tolerance {machine.tolerance_mm}mm may not meet {tolerance_needed_mm}mm requirement")

        # Compute weighted score (0-10)
        speed_w = priorities.get("speed", 0.3)
        precision_w = priorities.get("precision", 0.4)
        cost_w = priorities.get("cost", 0.3)

        # Normalize cost to 0-10 scale (cheaper = higher score)
        max_price = 150000  # Haas UMC-500 is ~$150k
        cost_score = max(0, 10 * (1 - machine.price_usd / max_price))

        score = (
            machine.speed_rating * speed_w
            + machine.precision_rating * precision_w
            + cost_score * cost_w
        )

        # Add best_for reasons
        for bf in machine.best_for:
            reasons.append(f"Best for: {bf}")

        return {
            "machine": machine.to_dict(),
            "score": round(score, 1),
            "fits_part": fits,
            "reasons": reasons,
            "warnings": warnings,
            "limitations": machine.limitations,
        }
