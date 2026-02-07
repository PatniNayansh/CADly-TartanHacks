# New Claude Code Session - Context Prompt

Copy and paste this into your new Claude Code session:

---

I'm working on **CADLY**, a DFM (Design for Manufacturing) AI agent for Fusion 360. This is a hackathon project. The previous session implemented a fake Dedalus UI for demos. I need your help creating 6 test CAD files and potentially hardcoding demo data.

## Quick Context

**What exists:**
- ✅ Full DFM analysis engine (detects wall thickness, holes, corners)
- ✅ Auto-fix system (works for all violation types)
- ✅ FastAPI server with UI on port 8080
- ✅ Fake Dedalus streaming UI (looks like AI, uses local analysis)
- ✅ Fusion 360 add-in on port 5000

**What I need now:**
- Create 6 test CAD files with specific violations
- Test the fake Dedalus UI with each file
- Potentially hardcode demo data if live analysis is unreliable

## Read These Files First

Please read these files to understand the project:

1. **PROJECT_STATUS.md** - Complete current state, architecture, what works
2. **FAKE_DEDALUS_README.md** - How the fake UI works
3. **CLAUDE.md** - Development guidelines
4. **src/dfm/rules.py** - DFM rules we're checking for

## My Current Goal

Create 6 test Fusion 360 files (`.f3d`) with known violations:

### Test File 1: test_thin_walls.f3d
- Simple box with 1mm thick walls
- Should trigger: FDM-001 (min wall thickness 2mm)
- Expected: 1 CRITICAL violation
- Auto-fix: Should thicken to 2mm

### Test File 2: test_small_holes.f3d
- Block with 2mm diameter holes
- Should trigger: FDM-003 (min hole diameter 3mm)
- Expected: Multiple WARNING violations
- Auto-fix: Should resize to 3mm

### Test File 3: test_sharp_corners.f3d
- Box with internal corners at 0mm radius (sharp 90° angles)
- Should trigger: CNC-001 (min corner radius 1.5mm)
- Expected: Multiple CRITICAL violations
- Auto-fix: Should add 1.5mm fillets

### Test File 4: test_non_standard_holes.f3d
- Block with 4.3mm diameter holes (non-standard size)
- Should trigger: GEN-001 (standard hole sizes)
- Expected: SUGGESTION violations
- Auto-fix: Should snap to 4.5mm standard

### Test File 5: test_combined.f3d
- Part with ALL violation types
- Should trigger: All rules
- Expected: 5+ violations of mixed severity
- Purpose: Test "Fix All" button

### Test File 6: test_clean.f3d
- Well-designed part with NO violations
- Should trigger: Nothing
- Expected: 0 violations, green checkmark, "Ready to manufacture"
- Purpose: Show success case

## Technical Details You Need

**DFM Rules** (from `src/dfm/rules.py`):
```python
FDM-001: Min wall thickness 2mm (CRITICAL)
FDM-003: Min hole diameter 3mm (WARNING)
CNC-001: Min internal corner radius 1.5mm (CRITICAL)
GEN-001: Standard hole sizes ±0.1mm (SUGGESTION)
SLA-001: Min wall thickness 1mm (CRITICAL)
```

**Fusion 360 Units**: Centimeters internally, but we convert to mm
**Server Port**: 8080 (NOT 3000)
**Fusion Port**: 5000

## What I Might Need Help With

1. **Creating the CAD files** - Specific dimensions to trigger violations
2. **Testing each file** - Run analysis and verify violations appear
3. **Hardcoding demo data** - If live analysis fails, create fallback data
4. **Demo script** - Timing and flow for presenting to judges

## How to Start

1. Read PROJECT_STATUS.md (tells you everything about current state)
2. Read src/dfm/rules.py (shows exact rules and thresholds)
3. Help me create the first test file (test_thin_walls.f3d)
4. We'll iterate through all 6 files

## Important Notes

- The server is already running on port 8080
- Fusion 360 should be open with the MCP add-in loaded
- The fake Dedalus UI streams analysis in 2-3 seconds
- All auto-fix functionality already works
- I just need test files with known, reliable violations

## Questions I Have

1. What exact dimensions should each test file have?
2. Should I create them manually in Fusion or use scripting?
3. If hardcoding is needed, where should the mock data go?
4. How do I ensure violations are reliably detected?

Ready to start! Please read PROJECT_STATUS.md first, then help me create the test files.
