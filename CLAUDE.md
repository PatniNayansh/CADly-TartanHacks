# CLAUDE.md - Cadly: DFM AI Agent for Fusion 360

## ⚠️ CRITICAL INSTRUCTION FOR CLAUDE

**DO ONE THING AT A TIME.** 

After completing each task:
1. Stop and verify it works
2. Commit the change
3. Ask what to do next

Do NOT attempt to build multiple features simultaneously. This is a hackathon - we need working code, not half-finished features.

---

## Project Overview

**Cadly** is an AI-powered Design for Manufacturing (DFM) assistant that integrates with Fusion 360 via MCP-Link. It detects manufacturing violations in CAD designs and suggests/applies fixes.

**Hackathon Timeline:** 4 days total (2 prep + 2 hackathon)
**Goal:** Working demo with core detection + basic auto-fix + simple UI

---

## Tech Stack (LOCKED - Do Not Change)

```
Backend:     Python 3.11+
Framework:   FastAPI
MCP:         MCP-Link for Fusion 360
Frontend:    HTML/CSS/JS (vanilla - no React, keep it simple)
Comms:       WebSockets for real-time updates
Testing:     pytest
```

**Why these choices:**
- FastAPI: Fast to write, async support, auto-docs
- Vanilla JS: No build step, faster iteration
- WebSockets: Real-time sidebar updates without polling

---

## Project Structure

```
cadly/
├── CLAUDE.md              # This file
├── README.md              # User-facing docs
├── requirements.txt       # Python dependencies
├── setup.py              # Package setup
│
├── src/
│   ├── __init__.py
│   ├── main.py           # FastAPI app entry point
│   │
│   ├── mcp/              # MCP-Link integration
│   │   ├── __init__.py
│   │   ├── client.py     # MCP client wrapper
│   │   └── geometry.py   # Geometry extraction helpers
│   │
│   ├── dfm/              # DFM rules engine
│   │   ├── __init__.py
│   │   ├── rules.py      # Rule definitions
│   │   ├── engine.py     # Rule evaluation
│   │   └── violations.py # Violation data classes
│   │
│   ├── analysis/         # Geometry analysis
│   │   ├── __init__.py
│   │   ├── walls.py      # Wall thickness detection
│   │   ├── holes.py      # Hole detection
│   │   ├── corners.py    # Corner radius detection
│   │   └── overhangs.py  # Overhang angle detection
│   │
│   ├── fixes/            # Auto-fix engine
│   │   ├── __init__.py
│   │   ├── base.py       # Base fix class
│   │   ├── wall_fix.py   # Wall thickness fix
│   │   ├── hole_fix.py   # Hole standardization
│   │   └── corner_fix.py # Corner radius fix
│   │
│   ├── api/              # FastAPI routes
│   │   ├── __init__.py
│   │   ├── routes.py     # REST endpoints
│   │   └── websocket.py  # WebSocket handlers
│   │
│   └── ui/               # Frontend
│       ├── index.html    # Main sidebar HTML
│       ├── styles.css    # Styling
│       └── app.js        # Frontend logic
│
├── tests/
│   ├── __init__.py
│   ├── test_rules.py
│   ├── test_analysis.py
│   └── test_fixtures/    # Test CAD files (STEP format)
│
├── data/
│   └── rules.json        # DFM rules database
│
└── scripts/
    ├── run_dev.py        # Dev server script
    └── test_mcp.py       # MCP connection test
```

---

## Development Workflow

### Before Writing ANY Code

1. **Understand the task completely** - Ask clarifying questions if unclear
2. **Check if similar code exists** - Don't duplicate
3. **Plan the approach** - Think before coding

### When Writing Code

1. **Write minimal code first** - Get it working, then improve
2. **Add types** - Use Python type hints everywhere
3. **Write docstrings** - Every function needs a one-liner at minimum
4. **Handle errors** - Always use try/except for external calls (MCP, file I/O)

### After Writing Code

1. **Test it** - Run the specific test or manual verification
2. **Commit** - Small, focused commits with clear messages
3. **Report back** - Tell the user what was done and what's next

---

## Coding Standards

### Python Style

```python
# GOOD - Type hints, docstring, error handling
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

# BAD - No types, no docstring, no error handling
async def get_wall_thickness(body_id):
    faces = await mcp_client.get_faces(body_id)
    walls = []
    for face in faces:
        opposite = find_opposite_face(face, faces)
        if opposite:
            thickness = calculate_distance(face, opposite)
            walls.append(Wall(face_id=face.id, thickness=thickness))
    return walls
```

### Data Classes for Everything

```python
from dataclasses import dataclass
from enum import Enum

class Severity(Enum):
    CRITICAL = "critical"
    WARNING = "warning"
    SUGGESTION = "suggestion"

@dataclass
class Violation:
    rule_id: str
    severity: Severity
    message: str
    feature_id: str
    current_value: float
    required_value: float
    fix_available: bool
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

## DFM Rules (Implement These)

### Priority 1 - Must Have (Day 1-2)

| ID | Rule | Process | Threshold | Severity |
|----|------|---------|-----------|----------|
| FDM-001 | Min wall thickness | FDM | 2mm | Critical |
| FDM-002 | Max overhang angle | FDM | 45° | Warning |
| CNC-001 | Min internal corner radius | CNC | 1.5mm | Critical |
| CNC-002 | Min feature size | CNC | 1mm | Critical |

### Priority 2 - Should Have (Day 3)

| ID | Rule | Process | Threshold | Severity |
|----|------|---------|-----------|----------|
| FDM-003 | Min hole diameter | FDM | 3mm | Warning |
| CNC-003 | Hole depth ratio | CNC | 4:1 max | Warning |
| GEN-001 | Standard hole sizes | All | ±0.1mm | Suggestion |

### Priority 3 - Nice to Have (Day 4)

| ID | Rule | Process | Threshold | Severity |
|----|------|---------|-----------|----------|
| FDM-004 | Max bridge length | FDM | 20mm | Warning |
| SLA-001 | Min wall thickness | SLA | 1mm | Critical |
| CNC-004 | Undercut detection | CNC | N/A | Critical |

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

## Hackathon Day-by-Day Plan

### Day -2 (Prep Day 1): Setup & Architecture
- [ ] Set up dev environment (WSL, Python, MCP-Link)
- [ ] Test MCP connection to Fusion 360
- [ ] Create project structure
- [ ] Implement basic geometry reading

### Day -1 (Prep Day 2): Core Detection
- [ ] Implement wall thickness detection
- [ ] Implement corner radius detection
- [ ] Implement hole detection
- [ ] Create DFM rules engine
- [ ] Test on sample parts

### Day 1 (Hackathon Day 1): API + Basic UI
- [ ] Build FastAPI endpoints
- [ ] Create WebSocket for real-time updates
- [ ] Build sidebar HTML/CSS
- [ ] Connect UI to backend
- [ ] Get end-to-end demo working

### Day 2 (Hackathon Day 2): Auto-Fix + Polish
- [ ] Implement wall thickness fix
- [ ] Implement corner radius fix
- [ ] Add one-click fix to UI
- [ ] Polish UI appearance
- [ ] Record demo video
- [ ] Prepare presentation

---

## Key Files to Create First

In this exact order:

1. `requirements.txt` - Dependencies
2. `src/dfm/violations.py` - Data classes
3. `src/dfm/rules.py` - Rule definitions
4. `src/mcp/client.py` - MCP wrapper
5. `src/analysis/walls.py` - First analysis module
6. `src/dfm/engine.py` - Rule evaluation
7. `src/main.py` - FastAPI app

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
```

---

## Common Pitfalls to Avoid

1. **Don't over-engineer** - We have 4 days. Simple > Perfect.

2. **Don't get stuck on MCP bugs** - If MCP-Link has issues, mock the data and move on. We can fix it later.

3. **Don't build features we won't demo** - Focus on what judges will see.

4. **Don't forget error handling** - One unhandled exception during demo = disaster.

5. **Don't skip the UI** - Judges are visual. A pretty UI with fewer features beats an ugly UI with more features.

---

## Demo Script (What We're Building Toward)

```
1. Open Fusion 360 with a sample part (phone case with intentional issues)
2. Show Cadly sidebar - it automatically detects 5 DFM violations
3. Click on a wall thickness violation - Fusion highlights the wall
4. Click "Fix Automatically" - wall thickens to 2mm in <1 second
5. Show cost estimate comparison (FDM vs CNC)
6. "Cadly saved 10 minutes of manual DFM checking"
```

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
- Handles curved walls

fix: handle missing faces in corner detection

- Add null check for face pairs
- Log warning instead of crashing
```

---

## Questions? Ask About:

1. How MCP-Link commands work
2. How to structure a specific feature
3. What to prioritize next
4. How to debug an issue

**Remember: One thing at a time. Working code > Perfect code.**


