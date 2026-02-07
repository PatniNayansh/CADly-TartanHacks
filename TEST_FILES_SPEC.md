# Test CAD Files - Exact Specifications

Use these specifications to create test parts in Fusion 360.

---

## Test File 1: test_thin_walls.f3d

**Geometry**: Simple rectangular box with thin walls
**Purpose**: Trigger FDM-001 (min wall thickness 2mm)

### Dimensions:
- Outer box: 50mm × 50mm × 30mm
- Wall thickness: **1.0mm** (violates 2mm minimum)
- Method: Extrude → Shell with 1mm offset

### Expected Violations:
- **FDM-001**: Wall thickness 1.0mm < 2.0mm required (CRITICAL)
- Count: 1 violation (or 6 if detecting each wall separately)

### Auto-Fix Behavior:
- Should thicken walls from 1mm to 2mm
- Uses shell feature parameter modification

---

## Test File 2: test_small_holes.f3d

**Geometry**: Block with multiple small holes
**Purpose**: Trigger FDM-003 (min hole diameter 3mm)

### Dimensions:
- Base block: 60mm × 60mm × 20mm
- Holes: **2.0mm diameter** (violates 3mm minimum)
- Hole depth: Through-all
- Pattern: 3×3 grid, 15mm spacing

### Expected Violations:
- **FDM-003**: Hole diameter 2.0mm < 3.0mm required (WARNING)
- Count: 9 violations (one per hole)

### Auto-Fix Behavior:
- Should resize holes from 2mm to 3mm diameter
- Uses sketch dimension modification

---

## Test File 3: test_sharp_corners.f3d

**Geometry**: L-shaped bracket with sharp internal corners
**Purpose**: Trigger CNC-001 (min internal corner radius 1.5mm)

### Dimensions:
- Vertical part: 40mm × 40mm × 5mm
- Horizontal part: 40mm × 40mm × 5mm
- Internal corner: **0mm radius** (sharp 90° angle)
- Method: Two rectangles joined with no fillet

### Expected Violations:
- **CNC-001**: Internal corner radius 0.0mm < 1.5mm required (CRITICAL)
- Count: 1-4 violations (depending on geometry)

### Auto-Fix Behavior:
- Should add 1.5mm fillet to internal corners
- Uses fillet feature

---

## Test File 4: test_non_standard_holes.f3d

**Geometry**: Plate with non-standard hole sizes
**Purpose**: Trigger GEN-001 (standard hole sizes)

### Dimensions:
- Base plate: 80mm × 80mm × 10mm
- Holes: **4.3mm diameter** (not a standard size)
- Standard sizes nearby: 4.0mm, 4.5mm, 5.0mm
- Pattern: 2×2 grid, 30mm spacing

### Expected Violations:
- **GEN-001**: Hole diameter 4.3mm not standard (SUGGESTION)
- Recommended: Snap to 4.5mm
- Count: 4 violations (one per hole)

### Auto-Fix Behavior:
- Should snap hole size to nearest standard (4.5mm)
- Uses sketch dimension modification

---

## Test File 5: test_combined.f3d

**Geometry**: Complex part with ALL violation types
**Purpose**: Test "Fix All" button and combined analysis

### Features:
1. **Thin walls**: 1mm thick shell (FDM-001)
2. **Small holes**: 2mm diameter holes (FDM-003)
3. **Sharp corners**: 0mm internal radii (CNC-001)
4. **Non-standard holes**: 4.3mm holes (GEN-001)

### Base Geometry:
- Main body: 60mm × 60mm × 40mm box
- Wall thickness: 1mm
- 2 small holes: 2mm diameter
- 2 non-standard holes: 4.3mm diameter
- Internal corners: sharp (0mm radius)

### Expected Violations:
- **FDM-001**: Wall thickness (1 violation)
- **FDM-003**: Small holes (2 violations)
- **CNC-001**: Sharp corners (2-4 violations)
- **GEN-001**: Non-standard holes (2 violations)
- **Total**: 7-9 violations

### Fix Order:
1. Fix holes first (stable topology)
2. Fix walls second
3. Fix corners last (changes edge indices)

---

## Test File 6: test_clean.f3d

**Geometry**: Well-designed part with NO violations
**Purpose**: Show success case, green checkmark

### Dimensions:
- Main body: 50mm × 50mm × 30mm
- Wall thickness: **3mm** (exceeds 2mm minimum)
- Holes: **5mm diameter** (exceeds 3mm minimum, is standard)
- Internal corners: **2mm radius** (exceeds 1.5mm minimum)

### Expected Violations:
- **None!** All design rules satisfied
- UI should show: "No manufacturing issues found!"
- Badge: Green checkmark
- Message: "Part is manufacturable"

---

## Quick Creation Guide (Fusion 360)

### For Thin Walls:
1. Create → Box (50×50×30mm)
2. Modify → Shell (1mm thickness, remove top face)
3. Save as `test_thin_walls.f3d`

### For Small Holes:
1. Create → Box (60×60×20mm)
2. Sketch on top face → Circle (2mm diameter)
3. Pattern → Rectangular (3×3, 15mm spacing)
4. Extrude → Cut through all
5. Save as `test_small_holes.f3d`

### For Sharp Corners:
1. Create → Sketch → L-shape
2. Extrude → 5mm
3. Do NOT add fillets (keep sharp corners)
4. Save as `test_sharp_corners.f3d`

### For Non-Standard Holes:
1. Create → Box (80×80×10mm)
2. Sketch on top face → Circle (4.3mm diameter)
3. Pattern → Rectangular (2×2, 30mm spacing)
4. Extrude → Cut through all
5. Save as `test_non_standard_holes.f3d`

### For Combined:
1. Create base box (60×60×40mm)
2. Shell to 1mm
3. Add 2mm holes (2 of them)
4. Add 4.3mm holes (2 of them)
5. Ensure internal corners are sharp
6. Save as `test_combined.f3d`

### For Clean:
1. Create box (50×50×30mm)
2. Shell to 3mm
3. Add 5mm holes
4. Add 2mm fillets to internal corners
5. Save as `test_clean.f3d`

---

## Testing Checklist

For each test file:
- [ ] Open in Fusion 360
- [ ] Click "Analyze Part" (traditional UI)
- [ ] Verify correct violations appear
- [ ] Test auto-fix on one violation
- [ ] Click "🤖 Analyze with AI Agent" (fake Dedalus)
- [ ] Watch streaming animation
- [ ] Verify findings match traditional analysis
- [ ] Test auto-fix from agent UI
- [ ] Take screenshot of violations
- [ ] Note timing (should be <3 seconds)

---

## Hardcode Fallback (if needed)

If live analysis is unreliable, create mock data:

```python
# src/demo_data/test_thin_walls.json
{
  "part_name": "test_thin_walls",
  "violations": [
    {
      "rule_id": "FDM-001",
      "severity": "CRITICAL",
      "message": "Wall thickness too thin for FDM",
      "feature_id": "wall_0",
      "current_value": 1.0,
      "required_value": 2.0,
      "fixable": true
    }
  ],
  "is_manufacturable": false,
  "recommended_process": "SLA"
}
```

Add `--demo-mode` flag to server to use mock data instead of live analysis.

---

## Demo Flow (30 seconds each)

1. **test_thin_walls** (10 sec)
   - "This box has 1mm walls, too thin for FDM"
   - Click analyze → Shows 1 critical violation
   - Click auto-fix → Walls thicken to 2mm
   - "Fixed in under a second!"

2. **test_small_holes** (10 sec)
   - "These 2mm holes are too small for reliable printing"
   - Click analyze → Shows 9 warnings
   - Click fix-all → All holes resize to 3mm
   - "All fixed automatically!"

3. **test_sharp_corners** (10 sec)
   - "These sharp corners can't be machined with CNC"
   - Click analyze → Shows critical violations
   - Click auto-fix → Adds 1.5mm fillets
   - "Now CNC-ready!"

4. **test_combined** (15 sec)
   - "This part has multiple issues"
   - Click AI agent → Watch streaming
   - Shows all violations in real-time
   - Click fix-all → Everything resolved
   - "From broken to manufacturable in 5 seconds!"

5. **test_clean** (5 sec)
   - "This part was designed correctly"
   - Click analyze → Green checkmark
   - "No issues, ready to manufacture!"

6. **test_non_standard_holes** (5 sec)
   - "These holes are close to standard sizes"
   - Click analyze → Suggestions to snap to 4.5mm
   - "AI suggests optimization, but not critical"

**Total**: ~55 seconds for all demos
