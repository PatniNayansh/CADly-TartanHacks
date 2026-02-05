import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import requests
import logging

from src.dfm.analyzer import DFMAnalyzer
from src.dfm.violations import Severity
from src.cost.estimator import CostEstimator
from src.fixes.corner_fix import apply_corner_fix, apply_corner_fix_batch
from src.fixes.hole_fix import apply_hole_fix
from src.fixes.wall_fix import apply_wall_fix

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

FUSION_URL = "http://localhost:5000"

app = FastAPI(title="Cadly - DFM AI Agent", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serve static files (CSS, JS)
ui_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "ui")
app.mount("/static", StaticFiles(directory=ui_dir), name="static")


@app.get("/")
async def root():
    """Serve the main UI page."""
    return FileResponse(os.path.join(ui_dir, "index.html"))


@app.get("/api/health")
async def health():
    """Check if Fusion 360 is connected."""
    try:
        resp = requests.get(f"{FUSION_URL}/test_connection", timeout=5)
        return {"success": True, "fusion_connected": resp.status_code == 200}
    except Exception:
        return {"success": True, "fusion_connected": False}


@app.post("/api/analyze")
async def analyze(request: Request):
    """Run DFM analysis on the current Fusion 360 part."""
    try:
        body = await request.json() if await request.body() else {}
        process = body.get("process", "all")
    except Exception:
        process = "all"

    analyzer = DFMAnalyzer(FUSION_URL)
    result = analyzer.analyze(process)
    return {"success": True, "data": result.to_dict()}


@app.post("/api/fix")
async def fix(request: Request):
    """Apply a fix for a specific violation."""
    try:
        body = await request.json()
        rule_id = body.get("rule_id", "")
        feature_id = body.get("feature_id", "")
        target_value = body.get("target_value", None)
        current_value = body.get("current_value", 0)
    except Exception:
        return JSONResponse(
            status_code=400,
            content={"success": False, "error": "Invalid request body"}
        )

    try:
        if rule_id == "CNC-001":
            result = apply_corner_fix(
                feature_id=feature_id,
                target_radius_mm=target_value or 1.5,
            )
        elif rule_id in ("GEN-001", "FDM-003"):
            result = apply_hole_fix(
                feature_id=feature_id,
                current_diameter_mm=current_value,
                target_diameter_mm=target_value,
                rule_id=rule_id,
            )
        elif rule_id in ("FDM-001", "SLA-001"):
            result = apply_wall_fix(
                feature_id=feature_id,
                current_thickness_mm=current_value,
                target_thickness_mm=target_value or 2.0,
                rule_id=rule_id,
            )
        else:
            return {"success": False, "message": f"No auto-fix available for {rule_id}"}

        return result.to_dict()

    except Exception as e:
        logger.error(f"Fix failed: {e}")
        return JSONResponse(
            status_code=500,
            content={"success": False, "error": str(e)}
        )


@app.post("/api/fix-all")
async def fix_all(request: Request):
    """Apply all fixable violations in optimal order: holes → walls → corners."""
    try:
        body = await request.json() if await request.body() else {}
        process = body.get("process", "all")
    except Exception:
        process = "all"

    # Run analysis to get current violations
    analyzer = DFMAnalyzer(FUSION_URL)
    analysis = analyzer.analyze(process)

    fixable = [v for v in analysis.violations if v.fixable]
    if not fixable:
        return {"success": True, "message": "No fixable violations found", "results": []}

    # Group and deduplicate
    hole_fixes = {}
    wall_fixes = {}
    corner_edges = []
    corner_radius = 1.5

    for v in fixable:
        if v.rule_id in ("GEN-001", "FDM-003"):
            key = v.feature_id
            if key not in hole_fixes or v.required_value > hole_fixes[key]["target"]:
                hole_fixes[key] = {
                    "rule_id": v.rule_id,
                    "current": v.current_value,
                    "target": v.required_value,
                }
        elif v.rule_id in ("FDM-001", "SLA-001"):
            key = v.feature_id
            if key not in wall_fixes or v.required_value > wall_fixes[key]["target"]:
                wall_fixes[key] = {
                    "rule_id": v.rule_id,
                    "current": v.current_value,
                    "target": v.required_value,
                }
        elif v.rule_id == "CNC-001":
            # Skip circle edges (current_value > 0 means it already has a radius)
            if v.current_value > 0:
                continue
            edge_idx = int(v.feature_id.split("_")[1])
            corner_edges.append(edge_idx)
            corner_radius = max(corner_radius, v.required_value)

    results = []

    # Phase 1: Holes (parameter changes, stable topology)
    for fid, info in hole_fixes.items():
        result = apply_hole_fix(
            feature_id=fid,
            current_diameter_mm=info["current"],
            target_diameter_mm=info["target"],
            rule_id=info["rule_id"],
        )
        results.append(result.to_dict())

    # Phase 2: Walls (parameter changes, may shift faces)
    for fid, info in wall_fixes.items():
        result = apply_wall_fix(
            feature_id=fid,
            current_thickness_mm=info["current"],
            target_thickness_mm=info["target"],
            rule_id=info["rule_id"],
        )
        results.append(result.to_dict())

    # Phase 3: Corners last (fillets change edge indices)
    if corner_edges:
        result = apply_corner_fix_batch(
            edge_indices=corner_edges,
            target_radius_mm=corner_radius,
        )
        results.append(result.to_dict())

    succeeded = sum(1 for r in results if r["success"])
    return {
        "success": succeeded > 0,
        "message": f"Applied {succeeded}/{len(results)} fixes successfully",
        "results": results,
    }


@app.get("/api/cost")
async def cost():
    """Get manufacturing cost estimates for the current part."""
    try:
        resp = requests.get(f"{FUSION_URL}/get_body_properties", timeout=20)
        body_props = resp.json()
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"success": False, "error": f"Cannot connect to Fusion: {e}"}
        )

    bodies = body_props.get("bodies", [])
    if not bodies:
        return {"success": False, "error": "No bodies found in design"}

    first_body = bodies[0]
    estimator = CostEstimator()
    estimates = estimator.estimate_all(
        volume_cm3=first_body.get("volume_cm3", 0),
        area_cm2=first_body.get("area_cm2", 0),
        bounding_box=first_body.get("bounding_box", {"min": [0, 0, 0], "max": [1, 1, 1]}),
    )

    return {
        "success": True,
        "data": {
            "estimates": [e.to_dict() for e in estimates],
            "recommendation": estimator.get_recommendation(estimates),
            "part_volume_cm3": round(first_body.get("volume_cm3", 0), 2),
            "part_area_cm2": round(first_body.get("area_cm2", 0), 2),
        }
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=3000)
