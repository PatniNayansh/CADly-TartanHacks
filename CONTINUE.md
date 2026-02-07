# CONTINUATION FILE — Paste this into a new Claude Code session

## INSTRUCTIONS FOR NEW SESSION
Read CLAUDE.md and PROGRESS.md first. Then continue the task list below.

## PROJECT STATE
- Working directory: C:\Users\patni\Documents\Projects\cadly-v2
- Git branch: main
- Last commit: 2a78d59 — feat: add process switch simulator
- Current phase: Hackathon polish — targeting 7 TartanHacks prize tracks
- Fusion add-in location: C:\Users\patni\AppData\Roaming\Autodesk\Autodesk Fusion 360\API\AddIns\MCP\MCP.py
- Python venv: .venv/ (all deps installed including websockets)

## WHAT WAS COMPLETED (Sessions 3-4, 2026-02-06)
1. Sustainability polish: carbon equivalencies in savings tips, waste material labels + weight equivalencies, process score breakdown cards with sub-score bars, graceful Dedalus unavailable handling (lazy import + API key check + UI fallback)
2. Decision Summary Panel: consolidated "TL;DR" at top of Analysis tab showing recommended process, cost, green score, violation count
3. AI Design Review Board (R3): 4 specialist agents (CNC Expert, FDM Expert, Materials Engineer, Cost Optimizer) + synthesis via Dedalus. POST /api/review endpoint, background WebSocket push, collapsible agent cards UI, Powered by Dedalus badge
4. Demo Polish: tab fade transitions, analyze button spinner, fix button animation (Fixing -> Fixed! + card fade), violation slide-in, updated branding, about footer
5. Process Switch Simulator (R2): redesign_planner.py (step-by-step roadmap, templates for all 13 rules), comparison.py (side-by-side with verdict), /api/simulate endpoint, simulator.js UI (verdict banner, violation diff, cost impact, process comparison grid, redesign roadmap)

## GIT LOG (6 commits across sessions 3-4)
- f4c59c7 feat: polish sustainability tab for hackathon judges
- 65ce080 feat: add unified decision summary panel
- 0cf0611 feat: add AI design review board with 4 specialist agents
- 5fa2287 feat: wire AI design review API and render agent panels
- d067212 feat: UI polish and demo readiness
- 2a78d59 feat: add process switch simulator

## WHAT TO DO NEXT (in order)

### Priority 1: Phase 7 — Machine + Material Recommendation
- Create `data/machines.json` (15-20 real machines with specs: build volume, tolerance, materials, price)
- Create `data/materials.json` (20-30 materials with properties: strength, heat resistance, cost, density)
- Create `src/recommend/__init__.py`
- Create `src/recommend/machine_db.py` — load machines.json, filter by build volume + process
- Create `src/recommend/machine_matcher.py` — match part to machines, rank by fit
- Create `src/recommend/material_db.py` — load materials.json, filter by process
- Create `src/recommend/material_matcher.py` — match part needs to materials, spider chart data
- Implement `/api/machines` GET endpoint (currently returns 501)
- Implement `/api/materials` GET endpoint (currently returns 501)
- Create `src/ui/components/recommend.js` — machine + material recommendation UI
- Wire up Recommend tab in index.html (currently placeholder)

### Priority 2: Test Everything End-to-End with Fusion 360
- Start server, create test part, run full analysis
- Test each tab: Analysis, Costs, Simulator, Recommend, AI Review, Sustainability
- Fix any runtime bugs
- Test auto-fix workflow

### Priority 3: Pitch Prep
- Update README.md to be pitch-ready
- Create PITCH_NOTES.md with talking points per track

## TEST PART CREATION SCRIPT
The test part gets lost when Fusion restarts. Recreate via three sequential curl calls to port 5000 (use `"code"` param, not `"script"`):

1. Create box:
```
curl -X POST http://localhost:5000/execute_script -H "Content-Type: application/json" -d '{"code": "import adsk.core\nimport adsk.fusion\n\nsketch = rootComp.sketches.add(rootComp.xYConstructionPlane)\nlines = sketch.sketchCurves.sketchLines\np1 = adsk.core.Point3D.create(0, 0, 0)\np2 = adsk.core.Point3D.create(5, 0, 0)\np3 = adsk.core.Point3D.create(5, 3, 0)\np4 = adsk.core.Point3D.create(0, 3, 0)\nlines.addByTwoPoints(p1, p2)\nlines.addByTwoPoints(p2, p3)\nlines.addByTwoPoints(p3, p4)\nlines.addByTwoPoints(p4, p1)\nprof = sketch.profiles.item(0)\next = rootComp.features.extrudeFeatures\ninput = ext.createInput(prof, adsk.fusion.FeatureOperations.NewBodyFeatureOperation)\ninput.setDistanceExtent(False, adsk.core.ValueInput.createByReal(2))\next.add(input)\nresult[\"ok\"] = True"}'
```

2. Shell (1mm walls):
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
- Start server: `.venv\Scripts\python.exe -m uvicorn src.main:app --host 0.0.0.0 --port 3000 --app-dir .`
- execute_script uses `"code"` param (not `"script"`)
- Dedalus integration: dedalus_labs package used for AI Review + AI Sustainability. Lazy import handles missing package gracefully.
- Models exist for machines (src/models/machines.py) and materials (src/models/materials.py) already — use them.

## TARTANHACKS PRIZE TRACKS
1. Best Overall — full platform polish
2. Crosses 2+ Fields — Mfg Eng + AI/CS + Materials + Sustainability + Education
3. Most Significant Innovation — DFMPro competitor ($5k/yr -> free, real-time, auto-fix)
4. Best AI for Decision Support — Decision Summary, recommender, simulator, AI review
5. Best Use of Dedalus Labs — AI Review Board + AI Sustainability scoring
6. Sustainability — Green score, waste/carbon analysis, equivalencies
7. Societal Impact — "Democratizes manufacturing expertise"

## ARCHITECTURE
- 2-layer: FastAPI (port 3000) -> Fusion add-in HTTP (port 5000)
- src/fusion/ wraps HTTP calls to port 5000
- src/dfm/engine.py orchestrates analysis
- src/fixes/ applies fixes (hole, corner, wall)
- src/simulator/ process switch simulation (violation diff, cost delta, redesign roadmap)
- src/sustainability/ calculates waste, carbon, green score + AI enrichment
- src/agents/ runs 4-agent design review via Dedalus
- src/api/routes.py: 13 endpoints (health, analyze, cost, cost/compare, fix, fix-all, sustainability, simulate, review, machines, materials, report)

## RESUME COMMAND
After reading CLAUDE.md and PROGRESS.md, start with:
Phase 7 — Machine + Material Recommendation (create data files, recommend module, API endpoints, UI)
