"""Cadly Auto-Fix: Base utilities and data classes."""

from dataclasses import dataclass
import requests
import time
import json
import logging

logger = logging.getLogger(__name__)

FUSION_URL = "http://localhost:5000"


@dataclass
class FixResult:
    """Result of a single fix attempt."""
    success: bool
    rule_id: str
    feature_id: str
    message: str
    old_value: float
    new_value: float
    rolled_back: bool = False

    def to_dict(self) -> dict:
        return {
            "success": self.success,
            "rule_id": self.rule_id,
            "feature_id": self.feature_id,
            "message": self.message,
            "old_value": round(self.old_value, 3),
            "new_value": round(self.new_value, 3),
            "rolled_back": self.rolled_back,
        }


def fusion_get(endpoint: str, timeout: int = 20) -> dict:
    """GET request to Fusion add-in."""
    resp = requests.get(f"{FUSION_URL}/{endpoint}", timeout=timeout)
    resp.raise_for_status()
    data = resp.json()
    if "error" in data:
        raise RuntimeError(data["error"])
    return data


def fusion_post(endpoint: str, data: dict, timeout: int = 15) -> dict:
    """POST request to Fusion add-in."""
    resp = requests.post(
        f"{FUSION_URL}/{endpoint}",
        data=json.dumps(data),
        headers={"Content-Type": "application/json"},
        timeout=timeout,
    )
    resp.raise_for_status()
    return resp.json()


def fusion_undo() -> None:
    """Call Fusion undo and wait for it to process."""
    fusion_post("undo", {})
    time.sleep(0.5)


def wait_for_fusion(seconds: float = 1.0) -> None:
    """Wait for Fusion task queue to process a modification."""
    time.sleep(seconds)


def fusion_exec(code: str, timeout: int = 35) -> dict:
    """Execute Python code inside Fusion 360 and return the result dict."""
    resp = requests.post(
        f"{FUSION_URL}/execute_script",
        data=json.dumps({"code": code}),
        headers={"Content-Type": "application/json"},
        timeout=timeout,
    )
    resp.raise_for_status()
    data = resp.json()
    if "error" in data:
        raise RuntimeError(data["error"])
    return data
