"""Material waste estimation per manufacturing process."""

from src.models.sustainability import WasteEstimate

# Material densities (g/cm3)
DENSITY_PLA = 1.24          # FDM default
DENSITY_RESIN = 1.10        # SLA default
DENSITY_ALUMINUM = 2.70     # CNC default
DENSITY_ABS = 1.04          # Injection Molding default

# Waste factors
FDM_SUPPORT_FACTOR = 0.10   # 10% of part volume as support material
FDM_FAIL_RATE = 0.08        # 8% average failed print waste
SLA_SUPPORT_FACTOR = 0.15   # 15% supports + vat residue
IM_RUNNER_FACTOR = 0.05     # 5% runner/sprue waste


class WasteCalculator:
    """Estimates material waste for each manufacturing process."""

    def estimate_all(self, volume_cm3: float, bounding_box: dict | None = None) -> list[WasteEstimate]:
        """Estimate waste for all processes."""
        bb = bounding_box or {}
        return [
            self.estimate_fdm(volume_cm3),
            self.estimate_sla(volume_cm3),
            self.estimate_cnc(volume_cm3, bb),
            self.estimate_im(volume_cm3),
        ]

    def estimate_fdm(self, volume_cm3: float) -> WasteEstimate:
        """FDM: support material + failed print waste."""
        support_waste = volume_cm3 * FDM_SUPPORT_FACTOR
        fail_waste = volume_cm3 * FDM_FAIL_RATE
        total_waste = support_waste + fail_waste
        raw_material = volume_cm3 + total_waste
        waste_pct = (total_waste / raw_material) * 100 if raw_material > 0 else 0
        return WasteEstimate(
            process="FDM",
            part_volume_cm3=volume_cm3,
            raw_material_cm3=raw_material,
            waste_cm3=total_waste,
            waste_percent=waste_pct,
            waste_grams=total_waste * DENSITY_PLA,
            breakdown={
                "supports": round(support_waste * DENSITY_PLA, 2),
                "failed_prints": round(fail_waste * DENSITY_PLA, 2),
            },
        )

    def estimate_sla(self, volume_cm3: float) -> WasteEstimate:
        """SLA: supports + uncured resin residue."""
        support_waste = volume_cm3 * SLA_SUPPORT_FACTOR
        raw_material = volume_cm3 + support_waste
        waste_pct = (support_waste / raw_material) * 100 if raw_material > 0 else 0
        return WasteEstimate(
            process="SLA",
            part_volume_cm3=volume_cm3,
            raw_material_cm3=raw_material,
            waste_cm3=support_waste,
            waste_percent=waste_pct,
            waste_grams=support_waste * DENSITY_RESIN,
            breakdown={
                "supports_and_residue": round(support_waste * DENSITY_RESIN, 2),
            },
        )

    def estimate_cnc(self, volume_cm3: float, bounding_box: dict) -> WasteEstimate:
        """CNC: bounding box stock minus part volume (subtractive = high waste)."""
        stock_vol = self._bounding_box_volume(bounding_box)
        # Stock must be at least as large as the part
        if stock_vol < volume_cm3:
            stock_vol = volume_cm3 * 1.5  # fallback: assume 50% overhead
        waste_vol = stock_vol - volume_cm3
        waste_pct = (waste_vol / stock_vol) * 100 if stock_vol > 0 else 0
        return WasteEstimate(
            process="CNC",
            part_volume_cm3=volume_cm3,
            raw_material_cm3=stock_vol,
            waste_cm3=waste_vol,
            waste_percent=waste_pct,
            waste_grams=waste_vol * DENSITY_ALUMINUM,
            breakdown={
                "machining_chips": round(waste_vol * DENSITY_ALUMINUM, 2),
            },
        )

    def estimate_im(self, volume_cm3: float) -> WasteEstimate:
        """Injection Molding: runner/sprue waste."""
        runner_waste = volume_cm3 * IM_RUNNER_FACTOR
        raw_material = volume_cm3 + runner_waste
        waste_pct = (runner_waste / raw_material) * 100 if raw_material > 0 else 0
        return WasteEstimate(
            process="Injection Molding",
            part_volume_cm3=volume_cm3,
            raw_material_cm3=raw_material,
            waste_cm3=runner_waste,
            waste_percent=waste_pct,
            waste_grams=runner_waste * DENSITY_ABS,
            breakdown={
                "runner_sprue": round(runner_waste * DENSITY_ABS, 2),
            },
        )

    @staticmethod
    def _bounding_box_volume(bb: dict) -> float:
        """Calculate volume from bounding box min/max arrays."""
        bb_min = bb.get("min", [0, 0, 0])
        bb_max = bb.get("max", [1, 1, 1])
        return abs(
            (bb_max[0] - bb_min[0])
            * (bb_max[1] - bb_min[1])
            * (bb_max[2] - bb_min[2])
        )
