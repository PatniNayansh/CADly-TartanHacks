# CONTINUATION FILE — Paste this into a new Claude Code session

## INSTRUCTIONS FOR NEW SESSION
Read CLAUDE.md, PROGRESS.md, and FUSION_SCRIPTING_LESSONS.md first. Then continue the task list below.

## PROJECT STATE
- Working directory: C:\Users\patni\Documents\Projects\cadly-v2
- Git branch: master
- Last commit: 8898f2a — fix: fix 4 known bugs (hole depth, wall fix shells, corner validation, websocket)
- Current phase: UI polish, then Phase 6
- Fusion add-in location: C:\Users\patni\AppData\Roaming\Autodesk\Autodesk Fusion 360\API\AddIns\MCP\MCP.py
- Python venv: .venv/ (all deps installed including websockets)

## WHAT WAS COMPLETED THIS SESSION (2026-02-06)
1. Hole depth detection FIXED — replaced edge-projection with bounding-box projection onto cylinder axis. Works for blind + through holes. CNC-003 now fires correctly (ratio 10.0 on 20mm deep, 2mm diameter hole).
2. Wall fix shell support ADDED — added shellFeatures fallback in wall_fix.py. Tested: "Increased wall from 1.0mm to 2.0mm (via shellThickness)".
3. Corner fix validation IMPROVED — now checks for arc edges at applied radius (not just edge count change). Message shows "(capped from 1.5mm to protect thin walls)" when radius is reduced. Tested: 0.4mm fillet on 1mm walls.
4. WebSocket FIXED — installed missing websockets package in .venv (was in requirements.txt but not installed).
5. Process filter UI COMMITTED — client-side filtering of violations by process dropdown (was uncommitted from prior session).
6. FUSION_SCRIPTING_LESSONS.md updated with lessons 15-19.
7. PROGRESS.md fully updated with all test results.

## WHAT TO DO NEXT (in order)

### Priority 1: UI — Better Fix Descriptions (UX IMPROVEMENT)
When user clicks "Auto-Fix", they don't know WHAT geometry is being changed. The violation card shows a generic message.

**Plan (already designed):**
1. Add `formatLocation(loc)` helper — converts [x,y,z] cm to "(x, y, z) mm" string
2. Improve `getFixDescription(v)` to include location in each case:
   - Holes: "Hole at (25.0, 15.0) mm — resize from 2.0mm to 3.0mm diameter"
   - Walls: "Wall near (25.0, 29.5, 10.3) mm — thicken from 1.0mm to 2.0mm"
   - Corners: "Edge #14 near (50.0, 30.0) mm — add fillet (auto-capped for safety)"
   - Depth ratio: "Hole at (25.0, 16.0) mm — depth ratio 10.0 exceeds 4.0 max"
3. Add location badge on each violation card: `📍 (x, y, z) mm`
4. Add `.violation-location` CSS class (small, monospace, secondary color)

**Files to modify:**
- `src/ui/components/violations.js` — formatLocation(), getFixDescription(), card HTML
- `src/ui/styles.css` — .violation-location styling

### Priority 2: Continue Phase 6 — Process Switch Simulator
Phase 6 has 2 uncommitted files already: `src/simulator/__init__.py`, `src/simulator/process_switch.py`.
Still needs:
- `src/simulator/redesign_planner.py` — generate step-by-step redesign roadmap
- `src/simulator/comparison.py` — side-by-side process comparison
- API routes in `src/api/routes.py` — POST /api/simulate endpoint
- UI component `src/ui/components/simulator.js` — process switch panel

The simulator should:
1. Take current violations + a target process
2. Re-run ALL rules for the target process against same geometry
3. Show: removed violations, new violations, persistent violations, cost delta
4. Generate redesign steps to make part compatible with new process

### Priority 3: Phase 7 — Machine + Material Recommendation
- Create `data/machines.json` (15-20 real machines with specs)
- Create `data/materials.json` (20-30 materials with properties)
- `src/recommend/machine_db.py`, `machine_matcher.py`
- `src/recommend/material_db.py`, `material_matcher.py`
- `src/ui/components/recommend.js`

## TEST PART CREATION SCRIPT
The test part gets lost when Fusion restarts. Recreate via three sequential curl calls to port 5000 (use `"code"` param, not `"script"`):

1. Create box:
```
curl -X POST http://localhost:5000/execute_script -H "Content-Type: application/json" -d '{"code": "import adsk.core\nimport adsk.fusion\n\nsketch = rootComp.sketches.add(rootComp.xYConstructionPlane)\nlines = sketch.sketchCurves.sketchLines\np1 = adsk.core.Point3D.create(0, 0, 0)\np2 = adsk.core.Point3D.create(5, 0, 0)\np3 = adsk.core.Point3D.create(5, 3, 0)\np4 = adsk.core.Point3D.create(0, 3, 0)\nlines.addByTwoPoints(p1, p2)\nlines.addByTwoPoints(p2, p3)\nlines.addByTwoPoints(p3, p4)\nlines.addByTwoPoints(p4, p1)\nprof = sketch.profiles.item(0)\next = rootComp.features.extrudeFeatures\ninput = ext.createInput(prof, adsk.fusion.FeatureOperations.NewBodyFeatureOperation)\ninput.setDistanceExtent(False, adsk.core.ValueInput.createByReal(2))\next.add(input)\nresult[\"ok\"] = True"}'
```

2. Shell (1mm walls — use ObjectCollection for face input):
```
curl -X POST http://localhost:5000/execute_script -H "Content-Type: application/json" -d '{"code": "import adsk.core\nimport adsk.fusion\n\nbody = rootComp.bRepBodies.item(rootComp.bRepBodies.count - 1)\nfaces = body.faces\ntop_face = None\nmax_z = -999\nfor i in range(faces.count):\n    f = faces.item(i)\n    c = f.centroid\n    if c.z > max_z:\n        max_z = c.z\n        top_face = f\n\nface_col = adsk.core.ObjectCollection.create()\nface_col.add(top_face)\nshells = rootComp.features.shellFeatures\ninput_obj = shells.createInput(face_col, False)\ninput_obj.insideThickness = adsk.core.ValueInput.createByReal(0.1)\nshells.add(input_obj)\nresult[\"ok\"] = True"}'
```

3. Hole (2mm diameter):
```
curl -X POST http://localhost:5000/execute_script -H "Content-Type: application/json" -d '{"code": "import adsk.core\nimport adsk.fusion\n\nsketch = rootComp.sketches.add(rootComp.xYConstructionPlane)\ncircles = sketch.sketchCurves.sketchCircles\ncircles.addByCenterRadius(adsk.core.Point3D.create(2.5, 1.5, 0), 0.1)\nprof = sketch.profiles.item(0)\next = rootComp.features.extrudeFeatures\ninput = ext.createInput(prof, adsk.fusion.FeatureOperations.CutFeatureOperation)\ninput.setAllExtent(adsk.fusion.ExtentDirections.PositiveExtentDirection)\next.add(input)\nresult[\"ok\"] = True"}'
```

## IMPORTANT CONTEXT
- Fusion 360 internal units are CENTIMETERS. 1mm = 0.1cm.
- Fusion caches Python modules. If you edit the add-in, user must stop + start add-in in Fusion.
- Wall detection is server-side in src/fusion/geometry.py (NOT in the Fusion add-in).
- Fix validation: GET for queries, POST for mutations.
- Git: NO co-author lines. user.name="Nayansh Patni", user.email="patninayansh@gmail.com".
- DO ONE THING AT A TIME. User enforces this strictly.
- Process filter dropdown works — filters violations client-side by selected process.
- WebSocket IS working now (websockets package installed).
- Start server: `"C:\Users\patni\Documents\Projects\cadly-v2\.venv\Scripts\python.exe" -m uvicorn src.main:app --host 0.0.0.0 --port 3000 --app-dir "C:\Users\patni\Documents\Projects\cadly-v2"`
- execute_script uses `"code"` param (not `"script"`)
- Shell createInput requires ObjectCollection, not Python list
- For multi-body cut operations, set `input.participantBodies = [target_body]`

## KNOWN ISSUES
- CLAUDE.md still references src/mcp/ in the project structure (renamed to src/fusion/). Low priority.
- Hole depth on shelled parts returns shell wall thickness (correct — cylindrical face only spans material).
- Cost tab (quantity slider) — NOT TESTED YET.

## ARCHITECTURE
- 2-layer: FastAPI (port 3000) → Fusion add-in HTTP (port 5000)
- src/fusion/ directory wraps HTTP calls to port 5000
- src/dfm/engine.py orchestrates analysis: gets geometry → applies rules → returns violations
- src/fixes/ applies fixes: hole_fix (sketch resize), corner_fix (fillet), wall_fix (extrude depth + shell thickness)
- src/api/routes.py: POST /api/analyze, GET /api/cost, POST /api/fix, POST /api/fix-all

## RESUME COMMAND
After reading CLAUDE.md and PROGRESS.md, start with:
Implement Priority 1 — better fix descriptions in violation cards (src/ui/components/violations.js)
