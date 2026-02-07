"""REST API endpoints for Cadly v2."""

import asyncio
import logging
from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from src.fusion.client import FusionClient, FusionError
from src.dfm.engine import DFMEngine
from src.costs.estimator import CostEstimator
from src.costs.comparison import CostComparer
from src.fixes.fix_runner import FixRunner
from src.api.middleware import error_response, success_response
from src.api.websocket import manager

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api")


def _get_client() -> FusionClient:
    """Create a Fusion client instance."""
    return FusionClient()


# ---- Health ----

@router.get("/health")
async def health():
    """Check Fusion 360 connection status."""
    client = _get_client()
    try:
        connected = await client.health_check()
        return success_response({"fusion_connected": connected})
    except Exception:
        return success_response({"fusion_connected": False})
    finally:
        await client.close()


# ---- DFM Analysis ----

@router.post("/analyze")
async def analyze(request: Request):
    """Run full DFM analysis on the current Fusion 360 part."""
    try:
        body = await request.json() if await request.body() else {}
        process = body.get("process", "all")
    except Exception:
        process = "all"

    client = _get_client()
    try:
        await manager.send_status("Connecting to Fusion 360...")
        engine = DFMEngine(client)

        await manager.send_status("Analyzing geometry...", 0.2)
        report = await engine.analyze(process)

        await manager.send_status("Analysis complete!", 1.0)
        await manager.send_result("analysis", report.to_dict())

        return success_response(report.to_dict())

    except FusionError as e:
        logger.error(f"Fusion error during analysis: {e}")
        return error_response("FUSION_ERROR", str(e))
    except Exception as e:
        logger.error(f"Analysis failed: {e}")
        return error_response("ANALYSIS_FAILED", str(e))
    finally:
        await client.close()


# ---- Cost Estimation ----

@router.get("/cost")
async def cost():
    """Get cost estimates for the current part."""
    client = _get_client()
    try:
        from src.fusion.geometry import GeometryHelper
        geo = GeometryHelper(client)
        bodies = await geo.get_bodies()

        if not bodies:
            return error_response("NO_BODIES", "No bodies found in design", 404)

        body = bodies[0]
        estimator = CostEstimator()
        estimates = estimator.estimate_all(
            volume_cm3=body.volume_cm3,
            area_cm2=body.area_cm2,
            bounding_box=body.bounding_box,
            face_count=body.face_count,
        )

        return success_response({
            "estimates": [e.to_dict() for e in estimates],
            "recommendation": estimator.get_recommendation(estimates),
            "part_volume_cm3": round(body.volume_cm3, 4),
            "part_area_cm2": round(body.area_cm2, 4),
        })

    except FusionError as e:
        return error_response("FUSION_ERROR", str(e))
    except Exception as e:
        logger.error(f"Cost estimation failed: {e}")
        return error_response("COST_FAILED", str(e))
    finally:
        await client.close()


@router.post("/cost/compare")
async def cost_compare(request: Request):
    """Full cost comparison with quantity curves and crossover points."""
    try:
        body = await request.json() if await request.body() else {}
        quantity = body.get("quantity", 1)
    except Exception:
        quantity = 1

    client = _get_client()
    try:
        from src.fusion.geometry import GeometryHelper
        geo = GeometryHelper(client)
        bodies = await geo.get_bodies()

        if not bodies:
            return error_response("NO_BODIES", "No bodies found in design", 404)

        b = bodies[0]
        comparer = CostComparer()
        result = comparer.compare(
            volume_cm3=b.volume_cm3,
            area_cm2=b.area_cm2,
            bounding_box=b.bounding_box,
            face_count=b.face_count,
            quantity=quantity,
        )

        return success_response(result.to_dict())

    except FusionError as e:
        return error_response("FUSION_ERROR", str(e))
    except Exception as e:
        logger.error(f"Cost comparison failed: {e}")
        return error_response("COST_FAILED", str(e))
    finally:
        await client.close()


# ---- Fix Endpoints (placeholder — Phase 5 fills these in) ----

@router.post("/fix")
async def fix(request: Request):
    """Apply a fix for a specific violation."""
    try:
        body = await request.json()
    except Exception:
        return error_response("BAD_REQUEST", "Invalid request body", 400)

    client = _get_client()
    try:
        runner = FixRunner(client)
        result = await runner.fix_single(body)
        if result.success:
            return success_response(result.to_dict())
        else:
            return success_response(result.to_dict())  # Still 200, success=false in result
    except FusionError as e:
        return error_response("FUSION_ERROR", str(e))
    except Exception as e:
        logger.error(f"Fix failed: {e}")
        return error_response("FIX_FAILED", str(e))
    finally:
        await client.close()


@router.post("/fix-all")
async def fix_all(request: Request):
    """Apply all fixable violations in optimal order."""
    try:
        body = await request.json() if await request.body() else {}
        process = body.get("process", "all")
    except Exception:
        process = "all"

    client = _get_client()
    try:
        # Re-analyze to get current violations
        engine = DFMEngine(client)
        report = await engine.analyze(process)
        fixable = [v for v in report.violations if v.fixable]

        if not fixable:
            return success_response({"message": "No fixable violations found", "results": []})

        runner = FixRunner(client)
        results = await runner.fix_all(report.violations)
        succeeded = sum(1 for r in results if r.success)

        return success_response({
            "message": f"Applied {succeeded}/{len(results)} fixes successfully",
            "results": [r.to_dict() for r in results],
        })

    except FusionError as e:
        return error_response("FUSION_ERROR", str(e))
    except Exception as e:
        logger.error(f"Fix-all failed: {e}")
        return error_response("FIX_FAILED", str(e))
    finally:
        await client.close()


# ---- Sustainability ----

@router.get("/sustainability")
async def sustainability():
    """Get sustainability report for the current part.

    Returns formula-based scores immediately. Kicks off Dedalus AI scoring
    in the background — results arrive via WebSocket 'ai_sustainability' event.
    """
    client = _get_client()
    try:
        from src.fusion.geometry import GeometryHelper
        from src.sustainability.report_builder import SustainabilityReportBuilder

        geo = GeometryHelper(client)
        bodies = await geo.get_bodies()

        if not bodies:
            return error_response("NO_BODIES", "No bodies found in design", 404)

        body = bodies[0]
        builder = SustainabilityReportBuilder()

        # Immediate: formula-based report
        report = builder.build(
            volume_cm3=body.volume_cm3,
            bounding_box=body.bounding_box,
        )

        # Background: AI enrichment via Dedalus (non-blocking)
        asyncio.create_task(
            _run_ai_sustainability(builder, body.volume_cm3, body.bounding_box)
        )

        return success_response(report.to_dict())

    except FusionError as e:
        return error_response("FUSION_ERROR", str(e))
    except Exception as e:
        logger.error(f"Sustainability report failed: {e}")
        return error_response("SUSTAINABILITY_FAILED", str(e))
    finally:
        await client.close()


async def _run_ai_sustainability(builder, volume_cm3: float, bounding_box: dict | None):
    """Background task: run Dedalus AI scoring and push result via WebSocket."""
    try:
        await manager.send_status("AI agents analyzing sustainability...")
        ai_report = await builder.build_ai_report(volume_cm3, bounding_box)
        if ai_report:
            await manager.send_result("ai_sustainability", ai_report.to_dict())
            await manager.send_status("AI sustainability analysis complete!", 1.0)
        else:
            await manager.send_result("ai_sustainability", {"error": "AI analysis unavailable"})
    except Exception as e:
        logger.error(f"Background AI sustainability failed: {e}")
        await manager.send_result("ai_sustainability", {"error": str(e)})


# ---- Process Switch Simulator ----

@router.post("/simulate")
async def simulate(request: Request):
    """Simulate switching from one manufacturing process to another.

    Request body: { "from_process": "cnc", "to_process": "fdm" }
    Returns: violations diff, cost delta, redesign steps, comparison data.
    """
    try:
        body = await request.json()
    except Exception:
        return error_response("BAD_REQUEST", "Invalid request body", 400)

    from_process = body.get("from_process", "").strip().lower()
    to_process = body.get("to_process", "").strip().lower()

    valid_processes = {"fdm", "sla", "cnc", "injection_molding"}
    if from_process not in valid_processes or to_process not in valid_processes:
        return error_response(
            "BAD_REQUEST",
            f"Invalid process. Must be one of: {', '.join(sorted(valid_processes))}",
            400,
        )
    if from_process == to_process:
        return error_response("BAD_REQUEST", "From and to processes must be different", 400)

    client = _get_client()
    try:
        from src.simulator.process_switch import ProcessSwitcher
        from src.simulator.comparison import build_comparison

        await manager.send_status(f"Simulating switch: {from_process.upper()} \u2192 {to_process.upper()}...", 0.1)

        switcher = ProcessSwitcher(client)
        result = await switcher.simulate(from_process, to_process)
        result_dict = result.to_dict()

        comparison = build_comparison(from_process, to_process, result_dict)

        await manager.send_status("Simulation complete!", 1.0)

        return success_response({
            **result_dict,
            "comparison": comparison,
        })

    except FusionError as e:
        return error_response("FUSION_ERROR", str(e))
    except Exception as e:
        logger.error(f"Simulation failed: {e}")
        return error_response("SIMULATE_FAILED", str(e))
    finally:
        await client.close()


# ---- Recommendation Endpoints (placeholder — Phase 7) ----

@router.get("/machines")
async def machines():
    """Get machine recommendations. (Phase 7)"""
    return error_response("NOT_IMPLEMENTED", "Machine recommendations coming in Phase 7", 501)


@router.get("/materials")
async def materials():
    """Get material recommendations. (Phase 7)"""
    return error_response("NOT_IMPLEMENTED", "Material recommendations coming in Phase 7", 501)


# ---- AI Design Review ----

@router.post("/review")
async def review(request: Request):
    """Run AI design review with 4 specialist agents via Dedalus.

    Returns immediately with status. Full results arrive via WebSocket 'ai_review' event.
    """
    client = _get_client()
    try:
        from src.fusion.geometry import GeometryHelper
        from src.dfm.engine import DFMEngine

        geo = GeometryHelper(client)
        bodies = await geo.get_bodies()
        if not bodies:
            return error_response("NO_BODIES", "No bodies found in design", 404)

        body = bodies[0]

        # Run analysis to get violations + costs for context
        engine = DFMEngine()
        report = await engine.analyze(client)
        estimator = CostEstimator()
        cost_estimates = estimator.estimate_all(
            volume_cm3=body.volume_cm3,
            area_cm2=body.area_cm2,
            bounding_box=body.bounding_box,
            face_count=body.face_count,
        )

        # Package part data for agents
        part_data = {
            "part_name": report.part_name,
            "volume_cm3": round(body.volume_cm3, 4),
            "area_cm2": round(body.area_cm2, 4),
            "bounding_box": body.bounding_box,
            "face_count": body.face_count,
            "violations": [v.to_dict() for v in report.violations],
            "violation_count": report.violation_count,
            "critical_count": report.critical_count,
            "is_manufacturable": report.is_manufacturable,
            "cost_estimates": [e.to_dict() for e in cost_estimates],
        }

        # Fire background task — results arrive via WebSocket
        asyncio.create_task(_run_ai_review(part_data))

        return success_response({
            "status": "review_started",
            "message": "AI Design Review Board is analyzing your part. Results will arrive via WebSocket.",
        })

    except FusionError as e:
        return error_response("FUSION_ERROR", str(e))
    except Exception as e:
        logger.error(f"Review start failed: {e}")
        return error_response("REVIEW_FAILED", str(e))
    finally:
        await client.close()


async def _run_ai_review(part_data: dict):
    """Background task: run 4-agent design review and push results via WebSocket."""
    try:
        from src.agents.review_board import ReviewBoard
        from src.agents.report_synthesizer import format_review_for_ui

        await manager.send_status("AI agents reviewing your design...", 0.1)
        board = ReviewBoard()
        raw_review = await board.run_review(part_data)

        await manager.send_status("Synthesizing expert opinions...", 0.8)
        ui_review = format_review_for_ui(raw_review)

        await manager.send_result("ai_review", ui_review)
        await manager.send_status("AI Design Review complete!", 1.0)
    except Exception as e:
        logger.error(f"Background AI review failed: {e}")
        await manager.send_result("ai_review", {"error": str(e)})


# ---- Report Endpoint (placeholder — Phase 10) ----

@router.get("/report")
async def report():
    """Generate DFM report PDF. (Phase 10)"""
    return error_response("NOT_IMPLEMENTED", "Report generation coming in Phase 10", 501)
