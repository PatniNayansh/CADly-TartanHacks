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
    except Exception:
        return JSONResponse(
            status_code=400,
            content={"success": False, "error": "Invalid request body"}
        )

    try:
        if rule_id.startswith("CNC-001"):
            # Fix internal corner radius → add fillet
            edge_idx = int(feature_id.split("_")[1]) if "edge_" in feature_id else 0
            radius_cm = (target_value or 1.5) / 10.0  # mm to cm
            resp = requests.post(
                f"{FUSION_URL}/fillet_specific_edges",
                json={"edge_indices": [edge_idx], "radius": radius_cm},
                timeout=15,
            )
            return {"success": True, "message": f"Added {target_value or 1.5}mm fillet to edge {edge_idx}"}

        elif rule_id.startswith("FDM-001") or rule_id.startswith("SLA-001"):
            # Wall thickness fix - would need shell/extrude modification
            return {"success": False, "message": "Wall thickness fix not yet implemented. Modify sketch dimensions manually."}

        elif rule_id == "GEN-001":
            # Hole size standardization - would need hole feature modification
            return {"success": False, "message": "Hole resize not yet implemented. Modify hole diameter manually."}

        else:
            return {"success": False, "message": f"No auto-fix available for {rule_id}"}

    except Exception as e:
        logger.error(f"Fix failed: {e}")
        return JSONResponse(
            status_code=500,
            content={"success": False, "error": str(e)}
        )


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
