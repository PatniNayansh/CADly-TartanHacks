"""Energy consumption and carbon footprint estimation per process."""

from src.models.sustainability import CarbonEstimate

# Energy consumption per gram of material processed (kWh/g)
FDM_KWH_PER_GRAM = 0.07    # mid-range of 0.05-0.10
SLA_KWH_PER_GRAM = 0.10    # mid-range of 0.08-0.12
CNC_KWH_PER_GRAM = 0.22    # mid-range of 0.15-0.30 (includes coolant/tooling)
IM_KWH_PER_GRAM = 0.03     # injection molding is energy-efficient per part

# US grid average CO2 emissions
CARBON_FACTOR_KG_PER_KWH = 0.40

# Material densities (g/cm3) — same as waste_calculator
DENSITY_PLA = 1.24
DENSITY_RESIN = 1.10
DENSITY_ALUMINUM = 2.70
DENSITY_ABS = 1.04


class CarbonEstimator:
    """Estimates energy usage and CO2 emissions per manufacturing process."""

    def estimate_all(self, volume_cm3: float) -> list[CarbonEstimate]:
        """Estimate carbon footprint for all processes."""
        return [
            self._estimate("FDM", volume_cm3, DENSITY_PLA, FDM_KWH_PER_GRAM),
            self._estimate("SLA", volume_cm3, DENSITY_RESIN, SLA_KWH_PER_GRAM),
            self._estimate("CNC", volume_cm3, DENSITY_ALUMINUM, CNC_KWH_PER_GRAM),
            self._estimate("Injection Molding", volume_cm3, DENSITY_ABS, IM_KWH_PER_GRAM),
        ]

    def _estimate(self, process: str, volume_cm3: float, density: float, kwh_per_gram: float) -> CarbonEstimate:
        """Estimate for a single process."""
        mass_g = volume_cm3 * density
        energy = mass_g * kwh_per_gram
        carbon = energy * CARBON_FACTOR_KG_PER_KWH
        return CarbonEstimate(
            process=process,
            part_mass_grams=mass_g,
            energy_kwh=energy,
            carbon_kg=carbon,
            kwh_per_gram=kwh_per_gram,
            carbon_factor=CARBON_FACTOR_KG_PER_KWH,
        )
