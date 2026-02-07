"""Machine database — loads and queries machines.json."""

import json
import logging
from pathlib import Path
from src.models.machines import Machine

logger = logging.getLogger(__name__)

# Normalize JSON "type" values to internal lowercase keys
PROCESS_MAP = {
    "FDM": "fdm",
    "SLA": "sla",
    "CNC": "cnc",
    "Injection Molding": "injection_molding",
}


class MachineDB:
    """Load and query the machine database."""

    def __init__(self, data_path: str | None = None):
        if data_path is None:
            data_path = str(Path(__file__).resolve().parents[2] / "data" / "machines.json")
        self.machines: list[Machine] = []
        self._load(data_path)

    def _load(self, path: str) -> None:
        """Load machines from JSON file."""
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            self.machines = [Machine.from_dict(m) for m in data.get("machines", [])]
            logger.info(f"Loaded {len(self.machines)} machines")
        except Exception as e:
            logger.error(f"Failed to load machines: {e}")
            self.machines = []

    def get_all(self) -> list[Machine]:
        """Return all machines."""
        return self.machines

    def filter_by_process(self, process: str) -> list[Machine]:
        """Filter machines by manufacturing process (e.g. 'fdm', 'cnc')."""
        process_lower = process.strip().lower()
        return [
            m for m in self.machines
            if PROCESS_MAP.get(m.machine_type, m.machine_type.lower()) == process_lower
        ]

    def filter_by_build_volume(self, part_x_mm: float, part_y_mm: float, part_z_mm: float) -> list[Machine]:
        """Filter machines that can physically fit the part."""
        return [
            m for m in self.machines
            if m.build_volume.can_fit(part_x_mm, part_y_mm, part_z_mm)
        ]
