"""Material database — loads and queries materials.json."""

import json
import logging
from pathlib import Path
from src.models.materials import Material

logger = logging.getLogger(__name__)

# Normalize process names to lowercase keys
PROCESS_ALIASES = {
    "FDM": "fdm",
    "SLA": "sla",
    "CNC": "cnc",
    "Injection Molding": "injection_molding",
}


class MaterialDB:
    """Load and query the material database."""

    def __init__(self, data_path: str | None = None):
        if data_path is None:
            data_path = str(Path(__file__).resolve().parents[2] / "data" / "materials.json")
        self.materials: list[Material] = []
        self._load(data_path)

    def _load(self, path: str) -> None:
        """Load materials from JSON file."""
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            self.materials = [Material.from_dict(m) for m in data.get("materials", [])]
            logger.info(f"Loaded {len(self.materials)} materials")
        except Exception as e:
            logger.error(f"Failed to load materials: {e}")
            self.materials = []

    def get_all(self) -> list[Material]:
        """Return all materials."""
        return self.materials

    def filter_by_process(self, process: str) -> list[Material]:
        """Filter materials compatible with a manufacturing process."""
        process_lower = process.strip().lower()
        return [
            m for m in self.materials
            if any(
                PROCESS_ALIASES.get(p, p.lower()) == process_lower
                for p in m.processes
            )
        ]

    def filter_by_category(self, category: str) -> list[Material]:
        """Filter materials by category (thermoplastic, resin, metal, etc.)."""
        return [m for m in self.materials if m.category.lower() == category.lower()]
