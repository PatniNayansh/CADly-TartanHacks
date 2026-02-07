# Cadly v2 — Build Progress

## Last Updated: 2026-02-06 (Session 4)
## Current Phase: Hackathon polish — targeting 7 TartanHacks prize tracks
## Last Commit: feat: add process switch simulator

## Completed:
- [x] Phase 1: Core Infrastructure — DONE
- [x] Phase 2: Detection Engine — DONE
- [x] Phase 3: Cost Estimation — DONE
- [x] Phase 4: API + UI — DONE
- [x] Phase 5: Auto-Correct (R1) — DONE (all 3 fixes verified: hole, corner, wall)
- [x] Phase 12: Sustainability Module — DONE (waste, carbon, green score + Dedalus AI scoring)
- [x] Phase 12 Polish: Equivalencies, breakdown cards, Dedalus error handling — DONE
- [x] Phase 13: Decision Summary Panel — DONE
- [x] Phase 14: AI Design Review Board (R3) — DONE (4 specialists + synthesis via Dedalus)
- [x] Phase 15: Demo Polish — DONE (loading animations, transitions, branding, footer)
- [x] Phase 6: Process Switch Simulator (R2) — DONE (redesign planner, comparison, API, UI)
- [ ] Phase 7: Machine + Material Recommendation (S1, S2) — NOT STARTED
- [ ] Phase 8: Cost Dashboard (S3) — PARTIAL (quantity slider exists, needs polish)
- [ ] Phase 10: Report Generator (S4) — NOT STARTED

## Testing Status (Phases 1-5):
- [x] Server starts on port 3000, health check returns fusion_connected: true
- [x] UI loads in browser at localhost:3000
- [x] Test part created via execute_script (shelled box + 2mm hole)
- [x] Analysis runs: 5x FDM-001, 1x FDM-003, 13x CNC-001 detected
- [x] Cost estimates show in Analysis tab (FDM/SLA/CNC/IM)
- [x] Wall detection — FIXED server-side (parallel faces, not anti-parallel). 5x FDM-001 at 1mm ✓
- [x] Hole fix — WORKS. Resized 2mm→3mm via sketch circle, validation passes ✓
- [x] Corner fix — capped at 40% of min wall, RETESTED: "Added 0.4mm fillet (capped from 1.5mm)" ✓
- [x] Wall fix — shell support added, TESTED: "Increased wall from 1.0mm to 2.0mm (via shellThickness)" ✓
- [x] Hole depth detection — FIXED: bounding box projection method, returns correct depth (20mm on solid box) ✓
- [x] CNC-003 — now fires correctly: "Hole depth ratio 10.0 exceeds 4.0 maximum" ✓
- [ ] Cost tab (quantity slider) — NOT TESTED YET

## UX Issues Found:
- User doesn't know WHAT geometry they're fixing when clicking Auto-Fix buttons
- All process violations shown at once (FDM + CNC + SLA) — confusing. User should pick process first.

## Bugs Fixed (Session 2 — 2026-02-06):
1. Hole depth: replaced edge-projection with bounding-box projection onto cylinder axis. Works for blind + through holes.
2. Wall fix shells: added shellFeatures fallback — adjusts shell thickness when no cut-extrude found.
3. Corner fix validation: now checks for arc edges at applied radius (not just edge count). Message shows "(capped from X)" when radius is reduced.
4. WebSocket: installed missing websockets package in .venv (was in requirements.txt but not installed).

## Bugs Fixed (Session 1 — 2026-02-05):
1. Wall detection: moved server-side, parallel faces (dot≈+1) not anti-parallel (dot≈-1)
2. Fix validation: used POST for GET-only endpoints → 404 → false rollback. Changed to GET.
3. Corner fillet: radius capped at 40% of min wall thickness to prevent geometry destruction.

## Fusion Add-in Changes (not in cadly-v2 repo):
- _analyze_holes() rewritten: bounding-box projection for depth (was edge-projection, failed on blind holes)
- _analyze_walls() rewritten but SUPERSEDED — wall detection now done server-side
- All German messages translated to English (~35 strings)
- German comments translated to English
- Location: C:\Users\patni\AppData\Roaming\Autodesk\Autodesk Fusion 360\API\AddIns\MCP\MCP.py

## Files Created:

### Root
- requirements.txt ✅
- .env.example ✅
- .gitignore ✅
- CLAUDE.md ✅
- FUSION_SCRIPTING_LESSONS.md ✅

### src/
- src/__init__.py ✅
- src/config.py ✅ (centralized settings, ENDPOINTS dict with 42 Fusion HTTP paths)
- src/main.py ✅ (FastAPI app, mounts static, WS endpoint, includes router)

### src/models/
- src/models/__init__.py ✅
- src/models/violations.py ✅ (Severity, ManufacturingProcess, Violation, ViolationReport)
- src/models/geometry.py ✅ (Face, Edge, Body, Wall, Hole, Corner with from_dict())
- src/models/machines.py ✅ (Machine, BuildVolume with can_fit())
- src/models/materials.py ✅ (Material, MaterialProperty with spider_chart_data())
- src/models/costs.py ✅ (CostEstimate, CostBreakdown, QuantityPoint, CostComparison)

### src/fusion/
- src/fusion/__init__.py ✅
- src/fusion/client.py ✅ (FusionClient: async httpx, retries, health_check, execute_script)
- src/fusion/commands.py ✅ (40 typed async wrappers for all Fusion endpoints)
- src/fusion/geometry.py ✅ (GeometryHelper: get_bodies, get_faces, get_edges, get_walls, get_holes, get_all — walls computed server-side)

### src/dfm/
- src/dfm/__init__.py ✅
- src/dfm/rules.py ✅ (DFMRule dataclass, check(), format_message(), get_nearest_standard_drill())
- src/dfm/registry.py ✅ (RuleRegistry singleton, load from JSON, filter by process/category)
- src/dfm/engine.py ✅ (DFMEngine: analyze() + analyze_with_data() + _recommend_process())

### src/analysis/
- src/analysis/__init__.py ✅
- src/analysis/walls.py ✅ (WallAnalyzer)
- src/analysis/corners.py ✅ (CornerAnalyzer — concave edges only)
- src/analysis/holes.py ✅ (HoleAnalyzer — diameter, depth ratio, standard size)
- src/analysis/overhangs.py ✅ (OverhangAnalyzer — face normal Z component)
- src/analysis/features.py ✅ (FeatureExtractor — classify holes/walls/fillets)

### src/costs/
- src/costs/__init__.py ✅
- src/costs/estimator.py ✅ (CostEstimator: FDM/SLA/CNC/IM with constants)
- src/costs/quantity_curves.py ✅ (QuantityCurveCalculator: cost at 1-10000 units, crossover detection)
- src/costs/comparison.py ✅ (CostComparer: multi-process comparison + recommendations)

### src/api/
- src/api/__init__.py ✅
- src/api/middleware.py ✅ (CORS, request logging, error_response/success_response helpers)
- src/api/routes.py ✅ (health, analyze, cost, cost/compare, fix, fix-all + placeholders)
- src/api/websocket.py ✅ (ConnectionManager: connect, disconnect, broadcast, send_status)

### src/fixes/
- src/fixes/__init__.py ✅
- src/fixes/base.py ✅ (BaseFix ABC, FixResult dataclass, validate_with_retry, rollback)
- src/fixes/corner_fix.py ✅ (CornerFix: safe radius cap, single + batch fillet)
- src/fixes/hole_fix.py ✅ (HoleFix: sketch circle resize via execute_script)
- src/fixes/wall_fix.py ✅ (WallFix: cut-extrude depth + shell thickness adjustment)
- src/fixes/fix_runner.py ✅ (FixRunner: ordered holes->walls->corners, WS progress)

### src/ui/
- src/ui/index.html ✅ (tabbed layout: Analysis, Costs, Simulator, Recommend, AI Review)
- src/ui/styles.css ✅ (dark theme, tabs, violation cards, cost table, toast)
- src/ui/app.js ✅ (tab switching, WS connection, analysis + cost dashboard)
- src/ui/components/violations.js ✅ (renderSummary, renderViolations, renderCost, applyFix, fixAll)
- src/ui/utils/api.js ✅ (apiGet, apiPost, wsConnect, handleWsMessage, showToast)
- src/ui/utils/charts.js ✅ (placeholder for Phase 8)

### src/simulator/ (UNCOMMITTED — Phase 6 partial)
- src/simulator/__init__.py (created, not committed)
- src/simulator/process_switch.py (created, not committed)

### data/
- data/rules.json ✅ (13 DFM rules: FDM-001~004, SLA-001, CNC-001~005, GEN-001, IM-001~002)
- data/standard_holes.json ✅ (35 metric + 41 imperial drill sizes)

### scripts/
- scripts/test_mcp.py ✅

## Files Remaining (Phases 6-11):
- src/simulator/redesign_planner.py, comparison.py + UI component
- src/recommend/ (machine_db.py, machine_matcher.py, material_db.py, material_matcher.py)
- data/machines.json, data/materials.json
- src/agents/ (review_board.py, report_synthesizer.py, specialists/)
- src/reports/ (generator.py, templates/dfm_report.html)
- src/ui/components/ (simulator.js, recommend.js, costs.js, review.js)
- tests/

## Known Issues:
- CLAUDE.md still references src/mcp/ in the project structure (renamed to src/fusion/). Low priority.
- Hole depth on shelled parts returns shell thickness (correct — cylindrical face only spans material).

## Key Decisions Made:
- 2-layer architecture: FastAPI (port 3000) → Fusion add-in (port 5000). MCP Server eliminated.
- src/mcp/ renamed to src/fusion/ (direct HTTP, not MCP protocol)
- Wall detection done SERVER-SIDE from /get_faces_info (not in Fusion add-in). Avoids restart cycles.
- Fix validation uses GET for query endpoints, POST only for mutation endpoints.
- Corner fillet radius capped at 40% of min wall thickness.
- Async throughout with httpx.AsyncClient
- JSON-driven rules (data/rules.json) with registry pattern
- Git: user.name="Nayansh Patni", user.email="patninayansh@gmail.com", NO co-author lines
- Python venv at .venv/ with dependencies installed
- Injection Molding added as 4th process (high tooling + low unit cost model)

## Verified Working:
- End-to-end analysis: UI → API → Fusion → 19 violations + costs displayed
- Wall detection: 5x FDM-001 at 1mm on shelled box ✓
- Hole auto-fix: 2mm→3mm resize + validation ✓
- Hole depth: 20mm on solid box, CNC-003 fires with ratio 10.0 ✓
- Corner fix: 0.4mm fillet on 1mm walls, capped message shown ✓
- Wall fix on shells: 1mm→2mm via shellThickness parameter ✓
- WebSocket: connected after installing websockets package ✓
- Cost estimates: FDM $0.37, SLA $0.82, CNC $91.16, IM $11000.28 for test part
