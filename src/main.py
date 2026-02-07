import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi import FastAPI, Request, File, Form, UploadFile
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
import requests
import logging
import asyncio
import json

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
        resp = requests.get(f"{FUSION_URL}/get_body_properties", timeout=5)
        connected = resp.status_code == 200
        logger.info(f"Fusion health check: status={resp.status_code}, connected={connected}")
        return {"success": True, "fusion_connected": connected}
    except Exception as e:
        logger.warning(f"Fusion health check failed: {e}")
        return {"success": True, "fusion_connected": False}


@app.get("/api/debug/paths")
async def debug_paths():
    """Debug endpoint to show file paths."""
    import os
    return {
        "ui_dir": ui_dir,
        "ui_dir_exists": os.path.exists(ui_dir),
        "index_html_path": os.path.join(ui_dir, "index.html"),
        "index_html_exists": os.path.exists(os.path.join(ui_dir, "index.html")),
        "cwd": os.getcwd(),
        "__file__": __file__,
    }


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


@app.post("/api/agent/analyze")
async def agent_analyze(
    file: UploadFile = File(None),
    machine_text: str = Form(""),
    process: str = Form("all"),
    quantity: int = Form(1),
    use_fusion: bool = Form(True),
    strategy: str = Form("auto"),
    extraction_model: str = Form(""),
    reasoning_model: str = Form(""),
):
    """
    Fake Dedalus agent endpoint - streams SSE events using real local analysis.
    This creates a realistic AI streaming experience for demos while using fast local code.
    """

    async def event_generator():
        """Generate Server-Sent Events with realistic delays."""
        try:
            # Phase 1: Extraction (fake parsing)
            extraction_steps = [0, 0.25, 0.75, 1.0]
            for progress in extraction_steps:
                yield f"event: phase\ndata: {json.dumps({'type': 'phase', 'phase': 'extraction', 'message': '🔍 Parsing geometry...', 'progress': progress})}\n\n"
                await asyncio.sleep(0.25)

            # Model handoff (if auto strategy)
            if strategy == "auto":
                yield f"event: model_handoff\ndata: {json.dumps({'type': 'model_handoff', 'phase': 'reasoning', 'message': '🔄 Switching to Claude Sonnet for reasoning...', 'progress': 0.5})}\n\n"
                await asyncio.sleep(0.3)

            # Phase 2: Reasoning (call real analysis)
            reasoning_steps = [0, 0.25, 0.75, 1.0]
            for i, progress in enumerate(reasoning_steps):
                yield f"event: phase\ndata: {json.dumps({'type': 'phase', 'phase': 'reasoning', 'message': '🤖 Running AI-powered DFM analysis...', 'progress': progress})}\n\n"

                # Actually run analysis during reasoning phase (in background)
                if i == len(reasoning_steps) - 1:  # Last step
                    # Get real violations from local analyzer
                    analyzer = DFMAnalyzer(FUSION_URL)
                    analysis_result = analyzer.analyze(process)
                    violations = analysis_result.violations
                else:
                    await asyncio.sleep(0.375)

            # Stream findings (one per violation)
            for violation in violations:
                finding_data = {
                    'rule_id': violation.rule_id,
                    'severity': violation.severity.name,
                    'message': violation.message,
                    'feature_id': violation.feature_id,
                    'current_value': violation.current_value,
                    'required_value': violation.required_value,
                    'fix_available': violation.fixable,
                }
                yield f"event: finding\ndata: {json.dumps({'type': 'finding', 'data': finding_data})}\n\n"
                await asyncio.sleep(0.2)

            # Get real cost estimates
            try:
                resp = requests.get(f"{FUSION_URL}/get_body_properties", timeout=20)
                body_props = resp.json()
                bodies = body_props.get("bodies", [])
                first_body = bodies[0] if bodies else {}

                estimator = CostEstimator()
                cost_estimates = estimator.estimate_all(
                    volume_cm3=first_body.get("volume_cm3", 0),
                    area_cm2=first_body.get("area_cm2", 0),
                    bounding_box=first_body.get("bounding_box", {"min": [0, 0, 0], "max": [1, 1, 1]}),
                )
                cost_data = [e.to_dict() for e in cost_estimates]
            except Exception as e:
                logger.warning(f"Cost estimation failed: {e}")
                cost_data = []

            # Final report
            final_data = {
                'part_name': analysis_result.part_name,
                'is_manufacturable': analysis_result.is_manufacturable,
                'recommended_process': analysis_result.recommended_process,
                'findings': [
                    {
                        'rule_id': v.rule_id,
                        'severity': v.severity.name,
                        'message': v.message,
                        'feature_id': v.feature_id,
                        'current_value': v.current_value,
                        'required_value': v.required_value,
                        'fix_available': v.fixable,
                    }
                    for v in violations
                ],
                'blocking_issues': [
                    {
                        'rule_id': v.rule_id,
                        'severity': v.severity.name,
                        'message': v.message,
                        'feature_id': v.feature_id,
                        'current_value': v.current_value,
                        'required_value': v.required_value,
                        'fix_available': v.fixable,
                    }
                    for v in violations if v.severity == Severity.CRITICAL
                ],
                'warnings': [
                    {
                        'rule_id': v.rule_id,
                        'severity': v.severity.name,
                        'message': v.message,
                        'feature_id': v.feature_id,
                        'current_value': v.current_value,
                        'required_value': v.required_value,
                        'fix_available': v.fixable,
                    }
                    for v in violations if v.severity == Severity.WARNING
                ],
                'cost_estimates': cost_data,
                'cost_analysis': {
                    'strategy': strategy,
                    'total_cost': cost_data[0]['total_cost'] if cost_data else 0,
                }
            }

            yield f"event: final\ndata: {json.dumps({'type': 'final', 'data': final_data})}\n\n"

        except Exception as e:
            logger.error(f"Agent analysis failed: {e}")
            error_data = {
                'type': 'error',
                'message': f'Analysis failed: {str(e)}'
            }
            yield f"event: error\ndata: {json.dumps(error_data)}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive",
        }
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=3000)
