# CLAUDE.md - Cadly v2: AI-Powered DFM Agent for Fusion 360

## ⚠️ CRITICAL INSTRUCTION FOR CLAUDE

**DO ONE THING AT A TIME.**

After completing each task:
1. Stop and verify it works
2. Commit the change
3. Ask what to do next

Do NOT attempt to build multiple features simultaneously. This is a hackathon — we need working code, not half-finished features.

**Working code > Perfect code. Always.**

---

## Project Overview

**Cadly** is an AI-powered Design for Manufacturing (DFM) assistant that integrates with Fusion 360 via MCP-Link. It detects manufacturing violations in CAD designs, auto-fixes them, recommends machines/materials, simulates process switching, and runs multi-agent design reviews.

**Goal:** A complete DFM intelligence platform — not just violation detection, but a full manufacturing advisor.

---

## Feature Map (Priority Order)

Build these in EXACT order. Do not skip ahead.

### CORE (Must work first — everything else depends on these)

| # | Feature | Status | Description |
|---|---------|--------|-------------|
| C1 | MCP-Link Integration | 🔨 | Connect to Fusion 360, read/modify geometry |
| C2 | DFM Detection Engine | 🔨 | Detect all manufacturing violations |
| C3 | Cost Estimation | 🔨 | Estimate cost across FDM/CNC/SLA |
| C4 | FastAPI + WebSocket Server | 🔨 | Backend API with real-time updates |
| C5 | Web UI Sidebar | 🔨 | Clean sidebar showing violations + controls |

### REVOLUTIONARY FEATURES (Hackathon winners — build after core works)

| # | Feature | Description |
|---|---------|-------------|
| R1 | **DFM Auto-Correct** | One-click geometry fixes: thicken walls, add fillets, resize holes. User sees geometry change live in Fusion 360. |
| R2 | **Process Switch Simulator** | User clicks "What if CNC → FDM?" and instantly sees: new violations that appear, violations that disappear, cost delta, and a step-by-step redesign roadmap. No other tool does this. |
| R3 | **AI Design Review Board** | Multi-agent design review powered by Dedalus Labs. Specialized agents (CNC expert, FDM expert, materials engineer, cost optimizer) review the part, debate trade-offs, and produce a unified prioritized report. Uses Dedalus SDK for agent orchestration. |

### SIDE FEATURES (Solid additions — build after revolutionary features)

| # | Feature | Description |
|---|---------|-------------|
| S1 | **Machine Recommendation Engine** | Database of real CNC/FDM/SLA machines with specs (build volume, tolerance, materials). User enters quantity + precision needs → ranked machine recommendations with reasons. Flags machines that CAN'T make the part due to specific geometry. |
| S2 | **Material Selector** | Based on part geometry + requirements (strength, heat resistance, flexibility, cost), recommends materials with trade-off spider charts. Filters by what the recommended machine can actually use. |
| S3 | **Cost Comparison Dashboard** | Interactive cost breakdown: process vs process, material vs material, quantity slider (1 to 10,000). Shows crossover points (e.g., "CNC is cheaper above 500 units"). |
| S4 | **DFM Report Generator** | Export a professional PDF report: violations found, fixes applied, machine/material recommendations, cost analysis, before/after comparison. Something an engineer can email to their team. |

---

## Tech Stack (LOCKED — Do Not Change)

```
Backend:        Python 3.11+
Framework:      FastAPI
MCP:            MCP-Link for Fusion 360
Frontend:       HTML/CSS/JS (vanilla — no React, keep it simple)
Comms:          WebSockets for real-time updates
AI Agents:      Dedalus Labs SDK (for R3 only — NOT for core MCP)
Reports:        WeasyPrint or fpdf2 for PDF generation
Testing:        pytest
```

**Why these choices:**
- FastAPI: Fast to write, async support, auto-docs
- Vanilla JS: No build step, faster iteration during hackathon
- WebSockets: Real-time sidebar updates without polling
- Dedalus SDK: Multi-agent orchestration for design review (ONLY for R3 feature, keeps core MCP server fast)

---

## Project Structure

```
cadly-v2/
├── CLAUDE.md                # This file
├── README.md                # User-facing docs
├── requirements.txt         # Python dependencies
├── .env.example             # Environment variable template
├── .gitignore               # Git ignore rules
│
├── src/
│   ├── __init__.py
│   ├── main.py              # FastAPI app entry point
│   ├── config.py            # App configuration + constants
│   │
│   ├── mcp/                 # MCP-Link integration layer
│   │   ├── __init__.py
│   │   ├── client.py        # MCP client wrapper (connection, retries)
│   │   ├── geometry.py      # Geometry extraction helpers
│   │   └── commands.py      # Typed wrappers for each MCP command
│   │
│   ├── models/              # Shared data models (used everywhere)
│   │   ├── __init__.py
│   │   ├── violations.py    # Violation, Severity, ViolationReport
│   │   ├── geometry.py      # Face, Edge, Body, Wall, Hole, Corner
│   │   ├── machines.py      # Machine, MachineSpec, MachineCapability
│   │   ├── materials.py     # Material, MaterialProperty
│   │   └── costs.py         # CostEstimate, CostBreakdown, CostComparison
│   │
│   ├── dfm/                 # DFM rules engine
│   │   ├── __init__.py
│   │   ├── rules.py         # Rule definitions (all processes)
│   │   ├── engine.py        # Rule evaluation + violation detection
│   │   └── registry.py      # Rule registry (load from JSON + code)
│   │
│   ├── analysis/            # Geometry analysis modules
│   │   ├── __init__.py
│   │   ├── walls.py         # Wall thickness detection
│   │   ├── holes.py         # Hole detection + standard sizes
│   │   ├── corners.py       # Internal corner radius detection
│   │   ├── overhangs.py     # Overhang angle detection
│   │   └── features.py      # General feature extraction
│   │
│   ├── fixes/               # Auto-fix engine (R1)
│   │   ├── __init__.py
│   │   ├── base.py          # BaseFix abstract class
│   │   ├── wall_fix.py      # Thicken thin walls
│   │   ├── hole_fix.py      # Resize to standard drill sizes
│   │   ├── corner_fix.py    # Add fillets to sharp corners
│   │   └── fix_runner.py    # Orchestrates fixes, validates after
│   │
│   ├── simulator/           # Process Switch Simulator (R2)
│   │   ├── __init__.py
│   │   ├── process_switch.py    # Core "what-if" logic
│   │   ├── redesign_planner.py  # Generate step-by-step redesign roadmap
│   │   └── comparison.py        # Side-by-side process comparison
│   │
│   ├── agents/              # Dedalus-powered AI agents (R3)
│   │   ├── __init__.py
│   │   ├── review_board.py      # Multi-agent design review orchestrator
│   │   ├── specialists/
│   │   │   ├── __init__.py
│   │   │   ├── cnc_expert.py    # CNC manufacturing specialist agent
│   │   │   ├── fdm_expert.py    # FDM/3D printing specialist agent
│   │   │   ├── materials_eng.py # Materials engineering agent
│   │   │   └── cost_optimizer.py # Cost optimization agent
│   │   └── report_synthesizer.py # Combines agent opinions into final report
│   │
│   ├── recommend/           # Machine + Material recommendation (S1, S2)
│   │   ├── __init__.py
│   │   ├── machine_db.py        # Machine database + query engine
│   │   ├── machine_matcher.py   # Match part requirements to machines
│   │   ├── material_db.py       # Material database + properties
│   │   └── material_matcher.py  # Match part needs to materials
│   │
│   ├── costs/               # Cost engine (S3)
│   │   ├── __init__.py
│   │   ├── estimator.py         # Cost calculation per process
│   │   ├── quantity_curves.py   # Cost vs quantity modeling
│   │   └── comparison.py        # Multi-process cost comparison
│   │
│   ├── reports/             # PDF report generation (S4)
│   │   ├── __init__.py
│   │   ├── generator.py         # Main report builder
│   │   └── templates/           # HTML templates for PDF
│   │       └── dfm_report.html
│   │
│   ├── api/                 # FastAPI routes
│   │   ├── __init__.py
│   │   ├── routes.py            # REST endpoints
│   │   ├── websocket.py         # WebSocket handlers
│   │   └── middleware.py        # Error handling, CORS
│   │
│   └── ui/                  # Frontend
│       ├── index.html           # Main sidebar HTML
│       ├── styles.css           # Styling
│       ├── app.js               # Core frontend logic
│       ├── components/
│       │   ├── violations.js    # Violation list component
│       │   ├── simulator.js     # Process switch UI
│       │   ├── recommend.js     # Machine/material recommendation UI
│       │   ├── costs.js         # Cost comparison charts
│       │   └── review.js        # AI design review display
│       └── utils/
│           ├── api.js           # API client helpers
│           └── charts.js        # Chart rendering (Chart.js or D3)
│
├── data/
│   ├── rules.json               # DFM rules database
│   ├── machines.json            # Machine database (specs, capabilities)
│   ├── materials.json           # Material database (properties, costs)
│   └── standard_holes.json      # Standard drill sizes
│
├── tests/
│   ├── __init__.py
│   ├── test_rules.py
│   ├── test_analysis.py
│   ├── test_fixes.py
│   ├── test_simulator.py
│   ├── test_recommend.py
│   ├── test_costs.py
│   └── test_fixtures/           # Test CAD data (STEP files, mock geometry)
│
└── scripts/
    ├── run_dev.py               # Dev server script
    ├── test_mcp.py              # MCP connection test
    └── seed_data.py             # Populate machine/material databases
```

---

## Development Workflow

### Before Writing ANY Code
1. **Understand the task completely** — ask clarifying questions if unclear
2. **Check if similar code exists** — don't duplicate
3. **Plan the approach** — think before coding

### When Writing Code
1. **Write minimal code first** — get it working, then improve
2. **Add types** — use Python type hints everywhere
3. **Write docstrings** — every function needs a one-liner at minimum
4. **Handle errors** — always use try/except for external calls (MCP, file I/O, Dedalus API)
5. **Before writing any Fusion Python script (execute_script), read FUSION_SCRIPTING_LESSONS.md first.**

### After Writing Code
1. **Test it** — run the specific test or manual verification
2. **Commit** — small, focused commits with clear messages
3. **Report back** — tell the user what was done and what's next

---

## Coding Standards

### Python Style

```python
# GOOD — Type hints, docstring, error handling
async def get_wall_thickness(body_id: str) -> list[Wall]:
    """Extract all walls and their thicknesses from a body."""
    try:
        faces = await mcp_client.get_faces(body_id)
        walls = []
        for face in faces:
            opposite = find_opposite_face(face, faces)
            if opposite:
                thickness = calculate_distance(face, opposite)
                walls.append(Wall(face_id=face.id, thickness=thickness))
        return walls
    except MCPError as e:
        logger.error(f"Failed to get walls for body {body_id}: {e}")
        raise AnalysisError(f"Wall analysis failed: {e}")

# BAD — No types, no docstring, no error handling
async def get_wall_thickness(body_id):
    faces = await mcp_client.get_faces(body_id)
    # ...
```

### Data Classes for Everything

```python
from dataclasses import dataclass, field
from enum import Enum

class Severity(Enum):
    CRITICAL = "critical"
    WARNING = "warning"
    SUGGESTION = "suggestion"

class ManufacturingProcess(Enum):
    FDM = "fdm"
    SLA = "sla"
    CNC = "cnc"
    INJECTION_MOLDING = "injection_molding"

@dataclass
class Violation:
    rule_id: str
    severity: Severity
    message: str
    feature_id: str
    current_value: float
    required_value: float
    fix_available: bool
    process: ManufacturingProcess
    affected_geometry: list[str] = field(default_factory=list)
```

### API Response Format

```python
# All API responses follow this structure
{
    "success": True,
    "data": { ... },
    "error": None
}

# On error
{
    "success": False,
    "data": None,
    "error": {
        "code": "ANALYSIS_FAILED",
        "message": "Could not analyze geometry"
    }
}
```

---

## DFM Rules

### Priority 1 — Must Have (Core)

| ID | Rule | Process | Threshold | Severity |
|----|------|---------|-----------|----------|
| FDM-001 | Min wall thickness | FDM | 2mm | Critical |
| FDM-002 | Max overhang angle | FDM | 45° | Warning |
| FDM-003 | Min hole diameter | FDM | 3mm | Warning |
| CNC-001 | Min internal corner radius | CNC | 1.5mm | Critical |
| CNC-002 | Min feature size | CNC | 1mm | Critical |
| CNC-003 | Hole depth ratio | CNC | 4:1 max | Warning |
| GEN-001 | Standard hole sizes | All | ±0.1mm | Suggestion |

### Priority 2 — Should Have

| ID | Rule | Process | Threshold | Severity |
|----|------|---------|-----------|----------|
| FDM-004 | Max bridge length | FDM | 20mm | Warning |
| SLA-001 | Min wall thickness | SLA | 1mm | Critical |
| CNC-004 | Undercut detection | CNC | N/A | Critical |
| CNC-005 | Tool accessibility | CNC | N/A | Warning |
| IM-001 | Draft angle | Injection Molding | 1-2° | Critical |
| IM-002 | Uniform wall thickness | Injection Molding | ±10% | Warning |

---

## Feature Implementation Details

### R1: DFM Auto-Correct

**How it works:**
1. User clicks "Fix" on a violation in the sidebar
2. Backend identifies the fix type (wall thicken / fillet add / hole resize)
3. Fix module sends MCP commands to modify Fusion 360 geometry
4. Re-runs analysis to confirm fix worked
5. UI updates in real-time via WebSocket

**Fix types to implement:**
- `wall_fix.py` — modify sketch dimension to increase wall thickness
- `corner_fix.py` — add fillet to sharp internal corners
- `hole_fix.py` — resize hole to nearest standard drill size

**Critical:** Each fix must re-analyze after applying to confirm the violation is gone. If the fix breaks something else, roll back.

### R2: Process Switch Simulator

**How it works:**
1. User has a part analyzed for CNC
2. User clicks "Simulate: Switch to FDM"
3. System runs ALL FDM rules against the same geometry
4. Shows a comparison panel:
   - ✅ Violations that disappear (CNC-only rules no longer apply)
   - ❌ New violations that appear (FDM-specific issues)
   - 💰 Cost delta (FDM vs CNC for this geometry)
   - 📋 Redesign roadmap: ordered steps to make the part FDM-compatible

**Why this is impressive:** No existing tool does instant process switching with automated redesign planning. Engineers manually re-evaluate every time they consider a different process.

**Architecture:**
```python
@dataclass
class ProcessSwitchResult:
    from_process: ManufacturingProcess
    to_process: ManufacturingProcess
    removed_violations: list[Violation]      # No longer apply
    new_violations: list[Violation]           # Newly introduced
    persistent_violations: list[Violation]    # Still there
    cost_before: CostEstimate
    cost_after: CostEstimate
    redesign_steps: list[RedesignStep]        # Ordered fix plan
```

### R3: AI Design Review Board (Dedalus Labs)

**How it works:**
1. User clicks "Run AI Design Review"
2. Backend packages geometry data + violations + cost data
3. Sends to Dedalus SDK which orchestrates 4 specialist agents:
   - **CNC Expert**: Evaluates machinability, tool paths, fixturing concerns
   - **FDM Expert**: Evaluates printability, support needs, layer adhesion
   - **Materials Engineer**: Suggests optimal materials, flags material-geometry conflicts
   - **Cost Optimizer**: Finds the cheapest path that meets requirements
4. Agents produce individual assessments
5. Report synthesizer combines them into a prioritized recommendation
6. Result displays in the UI as an "expert panel" with collapsible sections

**Dedalus Integration:**
```python
from dedalus_labs import AsyncDedalus, DedalusRunner

async def run_design_review(part_data: dict) -> ReviewReport:
    client = AsyncDedalus()
    runner = DedalusRunner(client)

    # Each specialist runs as a separate agent call
    cnc_review = await runner.run(
        input=f"You are a CNC machining expert. Review this part: {json.dumps(part_data)}. "
              f"Evaluate machinability, tool access, fixturing, and tolerances. "
              f"Flag any features that are impossible or expensive to machine.",
        model="anthropic/claude-sonnet-4-5-20250929",
    )
    # ... similar for FDM, materials, cost agents

    # Synthesizer combines all opinions
    synthesis = await runner.run(
        input=f"You are a manufacturing review board chair. "
              f"Combine these expert opinions into a final recommendation: "
              f"CNC: {cnc_review.final_output} "
              f"FDM: {fdm_review.final_output} "
              f"Materials: {materials_review.final_output} "
              f"Cost: {cost_review.final_output}",
        model="anthropic/claude-sonnet-4-5-20250929",
    )

    return parse_review_report(synthesis.final_output)
```

**IMPORTANT:** Dedalus is ONLY used for R3. It does NOT touch the core MCP server or detection engine. This keeps the core system fast and the Dedalus integration isolated.

### S1: Machine Recommendation Engine

**Database structure (machines.json):**
```json
{
    "machines": [
        {
            "id": "prusa-mk4s",
            "name": "Prusa MK4S",
            "type": "FDM",
            "build_volume": {"x": 250, "y": 210, "z": 220},
            "tolerance_mm": 0.1,
            "layer_height_range": [0.05, 0.3],
            "materials": ["PLA", "PETG", "ABS", "ASA", "TPU"],
            "nozzle_sizes": [0.4, 0.6, 0.8],
            "price_usd": 799,
            "speed_rating": 7,
            "precision_rating": 8,
            "limitations": ["No heated chamber", "Max temp 290C"]
        }
    ]
}
```

**Matching logic:**
1. Filter: Remove machines that physically can't make the part (build volume too small, material not supported, tolerance too loose)
2. Rank: Score remaining machines by user preferences (precision vs speed vs cost)
3. Explain: For each recommendation, explain WHY — and for rejected machines, explain what geometric feature eliminates them

### S2: Material Selector

**Inputs:** Part geometry requirements + user preferences
**Outputs:** Ranked materials with spider chart data (strength, heat resistance, flexibility, cost, machinability)

### S3: Cost Comparison Dashboard

**Interactive elements:**
- Process selector (FDM / SLA / CNC / Injection Molding)
- Quantity slider (1 → 10,000)
- Material selector (filtered by process)
- Live cost curve showing crossover points

### S4: DFM Report Generator

**PDF includes:**
1. Part summary (name, dimensions, volume, bounding box)
2. Violations found (grouped by severity)
3. Fixes applied (before/after)
4. Process recommendation
5. Machine recommendation
6. Material recommendation
7. Cost analysis with charts
8. AI Design Review summary (if R3 was run)

---

## MCP-Link Commands Reference

### Reading Geometry

```python
# Get document info
await mcp.call("fusion360_get_document_info", {})

# Get all bodies in active component
await mcp.call("fusion360_get_bodies", {"component_id": "root"})

# Get faces of a body
await mcp.call("fusion360_get_faces", {"body_id": "body1"})

# Get face geometry details
await mcp.call("fusion360_get_face_geometry", {"face_id": "face1"})

# Get edges of a body
await mcp.call("fusion360_get_edges", {"body_id": "body1"})
```

### Modifying Geometry

```python
# Modify sketch dimension
await mcp.call("fusion360_set_dimension", {
    "sketch_id": "sketch1",
    "dimension_id": "d1",
    "value": 2.0
})

# Add fillet to edge
await mcp.call("fusion360_add_fillet", {
    "edge_ids": ["edge1", "edge2"],
    "radius": 1.5
})
```

---

## Dedalus Labs Integration Notes

**Install:** `pip install dedalus-labs`
**API Key:** Set `DEDALUS_API_KEY` in `.env`
**ONLY used in:** `src/agents/` directory for the AI Design Review Board (R3)

**Key patterns:**
```python
from dedalus_labs import AsyncDedalus, DedalusRunner

client = AsyncDedalus()  # Reads DEDALUS_API_KEY from env
runner = DedalusRunner(client)

response = await runner.run(
    input="Your prompt here",
    model="anthropic/claude-sonnet-4-5-20250929",
)
print(response.final_output)
```

**Rules for Dedalus usage:**
- NEVER use Dedalus in the critical path of MCP communication
- NEVER use Dedalus for real-time detection (too slow)
- ONLY use for the design review feature which is async and user-triggered
- Always handle Dedalus API errors gracefully — if Dedalus is down, the rest of Cadly still works
- Use structured output prompting (ask the model to return JSON) for parsing agent responses

---

## Build Order (Step by Step)

### Phase 1: Core Infrastructure
```
1. requirements.txt + .env.example + .gitignore + config.py
2. src/models/ — all data classes
3. src/mcp/client.py — MCP connection wrapper
4. src/mcp/commands.py — typed command wrappers
5. src/mcp/geometry.py — geometry extraction helpers
   → TEST: Can we connect to Fusion 360 and read a body?
   → COMMIT
```

### Phase 2: Detection Engine
```
6. src/analysis/walls.py — wall thickness detection
7. src/analysis/corners.py — corner radius detection
8. src/analysis/holes.py — hole detection
9. src/analysis/overhangs.py — overhang detection
10. src/dfm/rules.py + registry.py — rule definitions
11. src/dfm/engine.py — rule evaluation
12. data/rules.json — rule database
    → TEST: Run analysis on test part, verify violations detected
    → COMMIT
```

### Phase 3: Cost Estimation
```
13. src/costs/estimator.py — per-process cost calculation
14. src/costs/quantity_curves.py — quantity scaling
15. src/costs/comparison.py — multi-process comparison
    → TEST: Get cost estimates for a test part
    → COMMIT
```

### Phase 4: API + UI
```
16. src/api/routes.py — REST endpoints
17. src/api/websocket.py — WebSocket handlers
18. src/api/middleware.py — error handling
19. src/main.py — FastAPI app
20. src/ui/index.html + styles.css + app.js
21. src/ui/components/violations.js
    → TEST: Full end-to-end: open UI, analyze part, see violations
    → COMMIT
```

### Phase 5: Auto-Correct (R1)
```
22. src/fixes/base.py — base fix class
23. src/fixes/wall_fix.py
24. src/fixes/corner_fix.py
25. src/fixes/hole_fix.py
26. src/fixes/fix_runner.py
    → TEST: Fix a thin wall, verify it thickened
    → COMMIT
```

### Phase 6: Process Switch Simulator (R2)
```
27. src/simulator/process_switch.py
28. src/simulator/redesign_planner.py
29. src/simulator/comparison.py
30. src/ui/components/simulator.js
    → TEST: Switch CNC → FDM, verify new violations appear
    → COMMIT
```

### Phase 7: Machine + Material Recommendation (S1, S2)
```
31. data/machines.json — populate with 15-20 real machines
32. data/materials.json — populate with 20-30 materials
33. src/recommend/machine_db.py + machine_matcher.py
34. src/recommend/material_db.py + material_matcher.py
35. src/ui/components/recommend.js
    → TEST: Get machine recommendations for test part
    → COMMIT
```

### Phase 8: Cost Dashboard (S3)
```
36. src/ui/components/costs.js — interactive charts
    → TEST: Slide quantity, see cost curves update
    → COMMIT
```

### Phase 9: AI Design Review Board (R3 — Dedalus)
```
37. src/agents/specialists/cnc_expert.py
38. src/agents/specialists/fdm_expert.py
39. src/agents/specialists/materials_eng.py
40. src/agents/specialists/cost_optimizer.py
41. src/agents/review_board.py
42. src/agents/report_synthesizer.py
43. src/ui/components/review.js
    → TEST: Run review, get structured report back
    → COMMIT
```

### Phase 10: Report Generator (S4)
```
44. src/reports/templates/dfm_report.html
45. src/reports/generator.py
    → TEST: Generate PDF, verify all sections present
    → COMMIT
```

### Phase 11: Polish
```
46. README.md — clean user-facing docs
47. UI polish — animations, transitions, loading states
48. Error handling audit — make sure nothing crashes during demo
49. Demo rehearsal — run through the demo script 3 times
    → FINAL COMMIT
```

---

## Demo Script (What We're Building Toward)

```
1. Open Fusion 360 with a sample part (phone case with intentional DFM issues)
2. Show Cadly sidebar — it automatically detects 8 DFM violations
3. Click on a thin wall violation — Fusion highlights the wall in red
4. Click "Auto-Fix" — wall thickens to 2mm live in Fusion
5. Click "Switch to FDM" — simulator shows 3 new violations + $12 cost savings
6. Click "Recommend Machine" — shows top 3 FDM printers ranked by fit
7. Click "Recommend Material" — shows PETG as best match with spider chart
8. Click "AI Design Review" — 4 specialist agents review the part
9. Show the expert panel: CNC says "good", FDM says "add supports here"
10. Click "Export Report" — downloads professional PDF
11. "Cadly: your entire DFM workflow in one sidebar."
```

---

## Testing Commands

```bash
# Run all tests
pytest tests/ -v

# Run specific test file
pytest tests/test_rules.py -v

# Run with coverage
pytest tests/ --cov=src --cov-report=html

# Test MCP connection
python scripts/test_mcp.py

# Test Dedalus connection
python -c "from dedalus_labs import AsyncDedalus; print('Dedalus OK')"
```

---

## Environment Variables

```bash
# .env
MCP_LINK_HOST=localhost
MCP_LINK_PORT=3000
DEDALUS_API_KEY=your_key_here
LOG_LEVEL=INFO
```

---

## Common Pitfalls to Avoid

1. **Don't over-engineer** — we have limited time. Simple > Perfect.
2. **Don't get stuck on MCP bugs** — if MCP-Link has issues, mock the data and move on.
3. **Don't build features we won't demo** — focus on what judges will see.
4. **Don't forget error handling** — one unhandled exception during demo = disaster.
5. **Don't skip the UI** — judges are visual. Pretty UI with fewer features beats ugly UI with more.
6. **Don't let Dedalus failures crash the app** — wrap ALL Dedalus calls in try/except. Core Cadly must work without Dedalus.
7. **Don't call Dedalus in tight loops** — it's an API call, treat it like one. Batch data, send once.
8. **Don't hardcode machine/material data in Python** — keep it in JSON files so it's easy to add more.

---

## Git Commit Message Format

```
type: short description

- Bullet points for details
- Keep it concise

Types: feat, fix, docs, refactor, test, chore
```

Examples:
```
feat: add wall thickness detection

- Implements parallel face analysis
- Returns list of Wall objects with thickness

feat: add process switch simulator

- Supports CNC <-> FDM <-> SLA switching
- Generates redesign roadmap with ordered steps

feat: integrate Dedalus for AI design review

- 4 specialist agents: CNC, FDM, materials, cost
- Report synthesizer combines opinions
```

---

## Questions? Ask About:

1. How MCP-Link commands work
2. How to structure a specific feature
3. What to prioritize next
4. How to debug an issue
5. How to use the Dedalus SDK
6. Machine/material database schema

**Remember: One thing at a time. Working code > Perfect code. Test after every feature.**


## ⚠️ CONTEXT MANAGEMENT — READ THIS

You WILL run out of context during this project. Plan for it.

### Rules:

1. **After EVERY phase commit**, update `PROGRESS.md` in the project root with current state.
2. **After EVERY 3-4 file creations**, check if you're getting close to your limit. If you feel your context is getting long (you've created 10+ files, or had many back-and-forth exchanges), proactively tell the user: "Context is getting long. I'm writing a continuation file now."
3. **When context is running low OR when the user says "save progress"**, immediately write `CONTINUE.md` with everything needed to resume in a fresh session.

### PROGRESS.md format (update after every phase):

```markdown
# Cadly v2 — Build Progress

## Last Updated: [timestamp]
## Current Phase: [phase number and name]
## Last Commit: [commit message]

## Completed:
- [x] Phase 1: Core Infrastructure — DONE
- [x] Phase 2: Detection Engine — DONE
- [ ] Phase 3: Cost Estimation — IN PROGRESS

## Files Created:
- src/models/violations.py ✅
- src/models/geometry.py ✅
- src/mcp/client.py ✅
- [etc.]

## Files Remaining:
- src/costs/estimator.py
- src/costs/quantity_curves.py
- [etc.]

## Known Issues:
- [any bugs or incomplete items]

## Key Decisions Made:
- Using HTTP add-in on port 5000 (not MCP-Link)
- [other decisions]
```

### CONTINUE.md format (write when context is running low):

```markdown
# CONTINUATION FILE — Paste this into a new Claude Code session in /plan mode

## INSTRUCTIONS FOR NEW SESSION
Read CLAUDE.md and PROGRESS.md first. Then continue from where we left off.

## PROJECT STATE
- Working directory: [path]
- Git branch: main
- Last commit: [hash] — [message]
- Current phase: [number]
- Currently working on: [specific file or task]

## WHAT WAS JUST COMPLETED
[Describe what was just finished in the last session]

## WHAT TO DO NEXT
[Exact next steps, in order]
1. [specific task]
2. [specific task]
3. [specific task]

## IMPORTANT CONTEXT FROM THIS SESSION
[Any decisions, bugs encountered, patterns established that the new session needs to know]

## FILES THAT NEED CHANGES
[List any files that are partially complete or need modification]

## ARCHITECTURE NOTES
[Any architecture decisions that aren't in CLAUDE.md]

## RESUME COMMAND
After reading CLAUDE.md and PROGRESS.md, start with:
[exact task to do first]
```

### When the user says "save progress" or "context check":
1. Immediately write/update PROGRESS.md
2. Write CONTINUE.md
3. Commit both: `git add PROGRESS.md CONTINUE.md && git commit -m "chore: save progress for context continuation"`
4. Tell the user: "Progress saved. Start a new Claude Code session and paste the contents of CONTINUE.md in /plan mode."