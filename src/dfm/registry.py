"""Rule registry: loads rules from JSON, provides filtered access."""

import json
import logging
from pathlib import Path
from typing import Optional

from src.config import DATA_DIR
from .rules import DFMRule

logger = logging.getLogger(__name__)


class RuleRegistry:
    """Central registry of all DFM rules. Loads from data/rules.json.

    Singleton-like: create once, query many times. Rules are immutable
    after loading.
    """

    def __init__(self):
        self._rules: list[DFMRule] = []
        self._loaded = False

    def load(self, path: Optional[Path] = None) -> None:
        """Load rules from JSON file."""
        if path is None:
            path = DATA_DIR / "rules.json"

        try:
            with open(path, "r") as f:
                data = json.load(f)
            self._rules = [DFMRule.from_dict(r) for r in data["rules"]]
            self._loaded = True
            logger.info(f"Loaded {len(self._rules)} DFM rules from {path}")
        except Exception as e:
            logger.error(f"Failed to load rules from {path}: {e}")
            raise

    def _ensure_loaded(self) -> None:
        """Auto-load rules if not already loaded."""
        if not self._loaded:
            self.load()

    @property
    def all_rules(self) -> list[DFMRule]:
        """Get all loaded rules."""
        self._ensure_loaded()
        return list(self._rules)

    def get_rule(self, rule_id: str) -> Optional[DFMRule]:
        """Get a specific rule by ID."""
        self._ensure_loaded()
        for rule in self._rules:
            if rule.rule_id == rule_id:
                return rule
        return None

    def rules_for_process(self, process: str) -> list[DFMRule]:
        """Get all rules that apply to a specific manufacturing process."""
        self._ensure_loaded()
        if process == "all":
            return list(self._rules)
        return [r for r in self._rules if r.applies_to_process(process)]

    def rules_by_category(self, category: str) -> list[DFMRule]:
        """Get all rules in a specific category."""
        self._ensure_loaded()
        return [r for r in self._rules if r.category == category]

    def fixable_rules(self) -> list[DFMRule]:
        """Get all rules that have auto-fix support."""
        self._ensure_loaded()
        return [r for r in self._rules if r.fixable]


# Module-level singleton
_registry: Optional[RuleRegistry] = None


def get_registry() -> RuleRegistry:
    """Get the global rule registry (lazy-loaded singleton)."""
    global _registry
    if _registry is None:
        _registry = RuleRegistry()
    return _registry
