# CONTINUATION FILE — Paste this into a new Claude Code session

## INSTRUCTIONS FOR NEW SESSION
Read CLAUDE.md and PROGRESS.md first. Then continue the task list below.

## PROJECT STATE
- Working directory: C:\Users\patni\Documents\Projects\cadly-v2
- Git branch: main
- Last commit: fe5322f — docs: add pitch-ready README
- Current phase: Hackathon polish — targeting 7 TartanHacks prize tracks
- Fusion add-in location: C:\Users\patni\AppData\Roaming\Autodesk\Autodesk Fusion 360\API\AddIns\MCP\MCP.py
- Python venv: .venv/ (all deps installed including websockets)
- GitHub: https://github.com/PatniNayansh/CADly-TartanHacks (pushed and up to date)

## WHAT WAS COMPLETED (Session 5, 2026-02-07)
1. Phase 7 — Machine + Material Recommendation:
   - data/machines.json (16 real machines: 5 FDM, 3 SLA, 5 CNC, 3 IM)
   - data/materials.json (23 materials with full properties)
   - src/recommend/ module (machine_db, machine_matcher, material_db, material_matcher)
   - Replaced /api/machines and /api/materials 501 placeholders with real endpoints
   - src/ui/components/recommend.js (ranked cards, rating bars, spider chart bars)
   - Wired Recommend tab in index.html + styles in styles.css
2. README.md — pitch-ready for TartanHacks judges (architecture, prize tracks, how to run)
3. All 4 commits pushed to GitHub

## GIT LOG (4 commits in session 5)
- 474c659 feat: add machine and material databases
- 31d8afa feat: add machine and material recommendation engine
- c4d0189 feat: wire machine and material recommendation UI
- fe5322f docs: add pitch-ready README

## WHAT TO DO NEXT (in order)

### Priority 1: End-to-End Testing with Fusion 360
- Start server, create test part, run full analysis
- Test each tab: Analysis, Costs, Simulator, Recommend, AI Review, Sustainability
- Fix any runtime bugs
- Test auto-fix workflow

### Priority 2: Optional Features (if time permits)
- Phase 10: Report Generator (PDF export)
- Phase 8: Cost Dashboard polish (quantity slider UX)

### Priority 3: Final Polish
- Visual check of all 6 tabs in browser
- Demo rehearsal

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
- src/recommend/ machine + material matching from JSON databases
- src/sustainability/ calculates waste, carbon, green score + AI enrichment
- src/agents/ runs 4-agent design review via Dedalus
- src/api/routes.py: 13 endpoints (health, analyze, cost, cost/compare, fix, fix-all, sustainability, simulate, review, machines, materials, report)

## RESUME COMMAND
After reading CLAUDE.md and PROGRESS.md, start with:
End-to-end testing with Fusion 360 — or optional Phase 10 (Report Generator) if time permits.
