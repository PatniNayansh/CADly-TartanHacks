# CADLY Handoff — Phase 1: Auto-Fix Engine

## What is CADLY?

A DFM (Design for Manufacturing) AI agent for Fusion 360. It detects manufacturing violations in CAD designs and auto-fixes them.

**Architecture:**
- **Fusion Add-in** (`MCP/MCP.py`): Runs inside Fusion 360, HTTP server on port 5000, task queue pattern for thread safety
- **MCP Server** (`Server/MCP_Server.py`): FastMCP on port 8000, wraps Fusion HTTP API as MCP tools
- **FastAPI App** (`src/main.py`): DFM analysis + UI on port 3000

## What's Done

### execute_script endpoint (Steps 1-4) — COMPLETE & TESTED
Added an `execute_script` endpoint that runs arbitrary Python inside Fusion's main thread. This bypasses the limitation that API-created geometry doesn't create sketch dimension parameters.

**Files modified:**
1. `MCP/MCP.py` — Added execute_script handler in `process_task` (synchronous query pattern with `exec()`) + POST route. **IMPORTANT**: This file must also be copied to `C:\Users\patni\AppData\Roaming\Autodesk\Autodesk Fusion 360\API\AddIns\MCP\MCP.py` (Fusion loads from there). Currently both copies are in sync.
2. `Server/config.py` — Added `"execute_script"` endpoint URL
3. `Server/MCP_Server.py` — Added `execute_script` MCP tool
4. `src/fixes/base.py` — Added `fusion_exec()` helper function

### Hole Fix rewrite (Step 5) — CODE WRITTEN, HAS A BUG
File: `src/fixes/hole_fix.py`

**What it does:** Uses `fusion_exec()` to send a script that iterates `rootComp.sketches` → `sketchCircles` → matches by radius → sets `circle.radius = target_radius_cm`.

**Status:** When tested DIRECTLY (importing the function), it works:
```
FixResult(success=True, message='Resized hole from 2.80mm to 3.0mm')
```

**Bug:** When tested through the FastAPI `/api/fix` endpoint, the validation step fails:
```
"message": "Circle resized but hole geometry did not update, rolled back"
```
This means the circle IS being resized, but when we immediately query `analyze_holes` to validate, the Fusion feature tree hasn't recomputed yet, so the old diameter is returned. The code then thinks the fix failed and calls `fusion_undo()`.

**Likely fix:** Increase `wait_for_fusion(1.5)` at line 70 of `hole_fix.py` to maybe 2.5-3.0 seconds. Or the issue could be that the FastAPI async context causes different timing than direct Python execution.

### Wall Fix rewrite (Step 6) — COMPLETE & TESTED
File: `src/fixes/wall_fix.py`

**What it does:** Uses `fusion_exec()` to iterate `rootComp.features.extrudeFeatures`, finds cut operations (operation == 1), and reduces their depth to thicken the wall.

**Status:** Works perfectly when tested directly:
```
FixResult(success=True, message='Increased wall from 1.0mm to 2.0mm (reduced pocket depth via d4)')
```
Not yet tested through the FastAPI endpoint.

### Corner Fix — COMPLETE & TESTED
File: `src/fixes/corner_fix.py`

Works for individual edges. Batch mode (`apply_corner_fix_batch`) re-queries geometry after each successful fillet because edge indices go stale.

**Known limitation:** 1.5mm fillet fails on edges adjacent to 1mm walls (geometry too thin). The batch fix handles this gracefully — it tries each edge, skips failures, and reports how many succeeded.

### Frontend — COMPLETE
Files: `src/ui/index.html`, `src/ui/styles.css`, `src/ui/app.js`
Dark-themed UI with Analyze, Fix individual violations, Fix All, and Cost Estimate buttons.

### DFM Analysis Engine — COMPLETE
Files: `src/dfm/analyzer.py`, `src/dfm/rules.py`, `src/dfm/violations.py`
Queries Fusion geometry (walls, holes, edges) and checks against manufacturing rules.

### Cost Estimator — COMPLETE
File: `src/cost/estimator.py`
Estimates FDM, SLA, and CNC costs based on volume and bounding box.

## What Needs Fixing

### 1. Hole fix validation timing (PRIORITY)
The hole fix works but the validation after the fix queries too soon. In `src/fixes/hole_fix.py` line 70, `wait_for_fusion(1.5)` may need to be increased, or we need a retry loop for validation.

### 2. End-to-end test through UI
All three fixes work when called directly from Python. Need to verify they work correctly through the FastAPI endpoints and the web UI at http://localhost:3000.

### 3. Fix-all endpoint
`/api/fix-all` runs holes → walls → corners in sequence. Previously timed out because corner batch was slow. Should retest after all rewrites.

## Test Part

Run `python test_part.py` from the cadly directory (Fusion must be open with add-in loaded). Creates:
- 50x30x20mm box
- Pocket with 1mm walls (48x28mm, 19mm deep)
- 2.8mm hole, 15mm deep

Expected violations: FDM-001 (thin wall), CNC-001 (sharp corners), GEN-001 (non-standard hole), CNC-002 (hole depth ratio)

## How to Run

1. Fusion 360 must be running with the MCP add-in loaded (port 5000)
2. `cd C:\Users\patni\Documents\Projects\cadly`
3. `python -m uvicorn src.main:app --port 3000`
4. Open http://localhost:3000

## Key Technical Details

- Fusion internal unit is **centimeters**. Multiply by 10 for mm, by 20 for diameter→radius conversion
- Fusion API is NOT thread-safe. All operations go through `task_queue` + `TaskEventHandler`
- For geometry reads, use synchronous query pattern: UUID + `threading.Event` + `query_results` dict
- `body.volume` returns cm³, `body.area` returns cm²
- After each successful fillet, edge indices become STALE — must re-query geometry
- The add-in must be reloaded in Fusion after changes to MCP.py (Scripts and Add-Ins dialog → Stop → Run)

## Still TODO (Phase 1 completion)
- [ ] Fix hole fix validation timing bug
- [ ] Full end-to-end test through the web UI
- [ ] Git commit after everything works
- [ ] Then move on to Phase 2 (see CLAUDE.md for hackathon plan)
