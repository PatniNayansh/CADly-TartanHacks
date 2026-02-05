import requests
import logging
from .violations import Violation, Severity, DFMResult, ManufacturingProcess
from .rules import RULES, STANDARD_DRILL_SIZES_MM, get_nearest_standard_drill, check_rule

logger = logging.getLogger(__name__)

FUSION_URL = "http://localhost:5000"


class DFMAnalyzer:
    """Analyzes Fusion 360 geometry for DFM violations."""

    def __init__(self, fusion_url: str = FUSION_URL):
        self.fusion_url = fusion_url

    def analyze(self, process: str = "all") -> DFMResult:
        """Run full DFM analysis on the current Fusion 360 part."""
        try:
            body_props = self._get(f"{self.fusion_url}/get_body_properties")
            faces_info = self._get(f"{self.fusion_url}/get_faces_info")
            edges_info = self._get(f"{self.fusion_url}/get_edges_info")
            walls = self._get(f"{self.fusion_url}/analyze_walls")
            holes = self._get(f"{self.fusion_url}/analyze_holes")
        except Exception as e:
            logger.error(f"Failed to query Fusion 360: {e}")
            return DFMResult(
                part_name="Error",
                violations=[Violation(
                    "SYS-001", Severity.CRITICAL,
                    f"Cannot connect to Fusion 360: {e}",
                    "system", 0, 0, False
                )],
                is_manufacturable=False,
            )

        violations = []

        # Check wall thickness
        violations += self._check_walls(walls, process)

        # Check internal corners
        violations += self._check_corners(edges_info, process)

        # Check holes
        violations += self._check_holes(holes, process)

        # Check overhangs
        violations += self._check_overhangs(faces_info, process)

        # Build result
        bodies = body_props.get("bodies", [])
        first_body = bodies[0] if bodies else {}

        result = DFMResult(
            part_name=first_body.get("name", "Unknown"),
            violations=violations,
            is_manufacturable=not any(v.severity == Severity.CRITICAL for v in violations),
            body_volume_cm3=first_body.get("volume_cm3", 0),
            body_area_cm2=first_body.get("area_cm2", 0),
        )
        result.recommended_process = self._recommend_process(result)
        return result

    def _get(self, url: str) -> dict:
        """GET request to Fusion with error handling."""
        resp = requests.get(url, timeout=20)
        resp.raise_for_status()
        data = resp.json()
        if "error" in data:
            raise RuntimeError(data["error"])
        return data

    def _check_walls(self, walls_data: dict, process: str) -> list[Violation]:
        """Check wall thickness against rules."""
        violations = []
        wall_rules = [r for r in RULES if "Wall Thickness" in r.name]
        if process != "all":
            wall_rules = [r for r in wall_rules if r.process.value == process]

        for wall in walls_data.get("walls", []):
            thickness = wall["thickness_mm"]
            for rule in wall_rules:
                if not check_rule(rule, thickness):
                    violations.append(Violation(
                        rule_id=rule.rule_id,
                        severity=rule.severity,
                        message=rule.message_template.format(
                            value=thickness, threshold=rule.threshold
                        ),
                        feature_id=f"wall_{wall['face_index_1']}_{wall['face_index_2']}",
                        current_value=thickness,
                        required_value=rule.threshold,
                        fixable=rule.fixable,
                        location=wall.get("centroid"),
                    ))
        return violations

    def _check_corners(self, edges_data: dict, process: str) -> list[Violation]:
        """Check internal corner radius against CNC rules."""
        violations = []
        corner_rules = [r for r in RULES if "Corner Radius" in r.name]
        if process != "all":
            corner_rules = [r for r in corner_rules if r.process.value == process]

        if not corner_rules:
            return violations

        for edge in edges_data.get("edges", []):
            # Only check concave (internal) edges
            if not edge.get("is_concave", False):
                continue

            # Sharp edge = no fillet = radius 0
            edge_type = edge.get("type", "")
            if edge_type == "line":
                radius_mm = 0.0
            elif edge_type in ("arc", "circle"):
                radius_mm = edge.get("radius_cm", 0) * 10  # cm to mm
            else:
                continue

            for rule in corner_rules:
                if not check_rule(rule, radius_mm):
                    violations.append(Violation(
                        rule_id=rule.rule_id,
                        severity=rule.severity,
                        message=rule.message_template.format(
                            value=radius_mm, threshold=rule.threshold
                        ),
                        feature_id=f"edge_{edge['index']}",
                        current_value=radius_mm,
                        required_value=rule.threshold,
                        fixable=rule.fixable,
                        location=edge.get("start"),
                    ))
        return violations

    def _check_holes(self, holes_data: dict, process: str) -> list[Violation]:
        """Check hole diameter, depth ratio, and standard sizes."""
        violations = []

        for hole in holes_data.get("holes", []):
            diameter = hole["diameter_mm"]
            depth = hole["depth_mm"]
            ratio = hole["depth_to_diameter_ratio"]

            # FDM min hole diameter
            if process in ("all", "fdm"):
                fdm_rules = [r for r in RULES if r.rule_id == "FDM-003"]
                for rule in fdm_rules:
                    if not check_rule(rule, diameter):
                        violations.append(Violation(
                            rule_id=rule.rule_id,
                            severity=rule.severity,
                            message=rule.message_template.format(
                                value=diameter, threshold=rule.threshold
                            ),
                            feature_id=f"hole_{hole['face_index']}",
                            current_value=diameter,
                            required_value=rule.threshold,
                            fixable=rule.fixable,
                            location=hole.get("centroid"),
                        ))

            # CNC hole depth ratio
            if process in ("all", "cnc"):
                ratio_rules = [r for r in RULES if r.rule_id == "CNC-002"]
                for rule in ratio_rules:
                    if depth > 0 and not check_rule(rule, ratio):
                        violations.append(Violation(
                            rule_id=rule.rule_id,
                            severity=rule.severity,
                            message=rule.message_template.format(
                                value=ratio, threshold=rule.threshold
                            ),
                            feature_id=f"hole_{hole['face_index']}",
                            current_value=ratio,
                            required_value=rule.threshold,
                            fixable=rule.fixable,
                            location=hole.get("centroid"),
                        ))

            # Non-standard hole size
            nearest = get_nearest_standard_drill(diameter)
            deviation = abs(diameter - nearest)
            if deviation > 0.1:
                violations.append(Violation(
                    rule_id="GEN-001",
                    severity=Severity.SUGGESTION,
                    message=f"Hole diameter {diameter:.2f}mm is not a standard drill size (nearest: {nearest}mm)",
                    feature_id=f"hole_{hole['face_index']}",
                    current_value=diameter,
                    required_value=nearest,
                    fixable=True,
                    location=hole.get("centroid"),
                ))

        return violations

    def _check_overhangs(self, faces_data: dict, process: str) -> list[Violation]:
        """Check face normals for overhang angles (FDM printing)."""
        violations = []
        if process not in ("all", "fdm"):
            return violations

        overhang_rules = [r for r in RULES if r.rule_id == "FDM-002"]
        if not overhang_rules:
            return violations

        for face in faces_data.get("faces", []):
            if face.get("type") != "plane":
                continue

            normal = face.get("normal")
            if not normal:
                continue

            # Overhang angle = angle between face normal and Z-up vector
            # A face pointing straight down (0,0,-1) has 180° from Z-up
            # We care about the angle from vertical for downward-facing surfaces
            nz = normal[2]  # Z component of normal

            # Only check downward-facing surfaces (negative Z normal)
            if nz >= 0:
                continue

            # Angle from Z-down: acos(-nz) gives angle from straight down
            # Overhang angle from vertical = 180 - acos(nz)
            import math
            angle_from_down = math.degrees(math.acos(max(-1, min(1, -nz))))

            # Overhang angle is measured from vertical
            # angle_from_down = 0 means straight down (worst case, 90° overhang)
            # angle_from_down = 90 means horizontal face pointing sideways
            overhang_angle = 90 - angle_from_down

            if overhang_angle < 0:
                continue

            for rule in overhang_rules:
                if not check_rule(rule, overhang_angle):
                    violations.append(Violation(
                        rule_id=rule.rule_id,
                        severity=rule.severity,
                        message=rule.message_template.format(
                            value=overhang_angle, threshold=rule.threshold
                        ),
                        feature_id=f"face_{face['index']}",
                        current_value=overhang_angle,
                        required_value=rule.threshold,
                        fixable=rule.fixable,
                        location=face.get("centroid"),
                    ))

        return violations

    def _recommend_process(self, result: DFMResult) -> str:
        """Recommend the best manufacturing process based on violations."""
        # Count critical violations per process
        process_scores = {"fdm": 0, "sla": 0, "cnc": 0}

        for v in result.violations:
            if v.severity == Severity.CRITICAL:
                if v.rule_id.startswith("FDM"):
                    process_scores["fdm"] += 10
                elif v.rule_id.startswith("SLA"):
                    process_scores["sla"] += 10
                elif v.rule_id.startswith("CNC"):
                    process_scores["cnc"] += 10
            elif v.severity == Severity.WARNING:
                if v.rule_id.startswith("FDM"):
                    process_scores["fdm"] += 3
                elif v.rule_id.startswith("SLA"):
                    process_scores["sla"] += 3
                elif v.rule_id.startswith("CNC"):
                    process_scores["cnc"] += 3

        # Lower score = fewer violations = better process
        best = min(process_scores, key=process_scores.get)
        return best.upper()
