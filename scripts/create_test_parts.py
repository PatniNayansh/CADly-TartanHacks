"""
Create 6 test CAD parts in Fusion 360 for CADLY DFM demo.

Sends HTTP requests to the MCP add-in on port 5000.
Each part is built one-by-one with a pause for manual save.

ALL DIMENSIONS IN CENTIMETERS (Fusion internal unit).
  1mm = 0.1cm, 2mm = 0.2cm, 50mm = 5cm, etc.

Usage:
    python scripts/create_test_parts.py          # Build all 6 parts
    python scripts/create_test_parts.py 1        # Build only part 1
    python scripts/create_test_parts.py 3        # Build only part 3
"""

import requests
import time
import json
import sys

BASE = "http://localhost:5000"


def post(endpoint, data=None):
    """Send POST to Fusion MCP add-in."""
    try:
        r = requests.post(f"{BASE}{endpoint}", json=data or {}, timeout=30)
        print(f"  POST {endpoint}: {r.status_code} - {r.text[:100]}")
        time.sleep(1.5)
        return r
    except requests.exceptions.ConnectionError:
        print(f"  ERROR: Cannot connect to Fusion on port 5000. Is the MCP add-in running?")
        sys.exit(1)


def get(endpoint):
    """Send GET to Fusion MCP add-in."""
    try:
        r = requests.get(f"{BASE}{endpoint}", timeout=20)
        return r.json()
    except requests.exceptions.ConnectionError:
        print(f"  ERROR: Cannot connect to Fusion on port 5000.")
        sys.exit(1)


def execute_script(code):
    """Run arbitrary Python code inside Fusion 360 via /execute_script."""
    r = requests.post(f"{BASE}/execute_script", json={"code": code}, timeout=30)
    result = r.json()
    if "error" in result:
        print(f"  SCRIPT ERROR: {result['error']}")
    else:
        print(f"  Script executed OK")
    time.sleep(1.5)
    return result


def wait_for_user(part_name):
    """Pause so user can save as .f3d in Fusion."""
    print(f"\n{'*'*60}")
    print(f"  DONE building: {part_name}")
    print(f"  Save this as '{part_name}' in Fusion 360 (File > Save As)")
    print(f"  Then press Enter to continue...")
    print(f"{'*'*60}")
    input()


def clear():
    """Delete everything in the current design."""
    print("  Clearing workspace...")
    post("/delete_everything")
    time.sleep(2)


def health_check():
    """Verify Fusion MCP add-in is reachable."""
    print("Checking connection to Fusion 360...")
    try:
        r = requests.post(f"{BASE}/delete_everything", json={}, timeout=10)
        if r.status_code == 200:
            print("  Connected to Fusion 360 MCP add-in!")
            return True
    except:
        pass
    print("  ERROR: Cannot reach Fusion 360 on port 5000.")
    print("  Make sure Fusion 360 is open and the MCP add-in is loaded.")
    return False


# =============================================================================
# Part 1: Thin Walls - Triggers FDM-001
# =============================================================================
def create_thin_walls():
    """50x50x30mm box with 1mm walls (violates 2mm minimum)."""
    # All values in cm: 50mm=5cm, 30mm=3cm, 1mm=0.1cm
    print("\n  Step 1: Creating 50x50x30mm box (5x5x3 cm)...")
    post("/Box", {"height": 5, "width": 5, "depth": 3, "x": 0, "y": 0, "z": 0})
    time.sleep(1)

    print("  Step 2: Shelling to 1mm walls (0.1 cm)...")
    post("/shell_body", {"thickness": 0.1, "faceindex": 0})

    print("\n  Expected violations:")
    print("    - FDM-001: Wall thickness 1.0mm < 2.0mm (CRITICAL) x5")


# =============================================================================
# Part 2: Small Holes - Triggers FDM-003
# =============================================================================
def create_small_holes():
    """60x60x20mm block with 3x3 grid of 2mm holes (violates 3mm minimum)."""
    # 60mm=6cm, 20mm=2cm, 2mm diameter=0.2cm, 15mm spacing=1.5cm
    print("\n  Step 1: Creating 60x60x20mm block (6x6x2 cm)...")
    post("/Box", {"height": 6, "width": 6, "depth": 2, "x": 0, "y": 0, "z": 0})
    time.sleep(1)

    print("  Step 2: Adding 3x3 grid of 2mm diameter holes on TOP face...")
    # Points in cm, spaced 1.5cm apart, centered on face
    # faceindex 4 = top face (normal [0,0,1]) for a box extruded on XY plane
    points = [
        [-1.5, -1.5], [-1.5, 0], [-1.5, 1.5],
        [0, -1.5],    [0, 0],    [0, 1.5],
        [1.5, -1.5],  [1.5, 0],  [1.5, 1.5],
    ]
    post("/holes", {
        "points": points,
        "width": 0.2,      # 2mm diameter in cm
        "depth": 2,         # through-all (2cm = 20mm = block depth)
        "faceindex": 4,     # top face
    })

    print("\n  Expected violations:")
    print("    - FDM-003: Hole diameter 2.0mm < 3.0mm (WARNING) x9")


# =============================================================================
# Part 3: Sharp Corners - Triggers CNC-001
# =============================================================================
def create_sharp_corners():
    """L-shaped bracket with sharp 90-degree internal corners."""
    print("\n  Step 1: Creating L-shaped bracket via script...")

    # All Point3D coordinates in cm (Fusion internal unit)
    # L is 40mm=4cm tall, 40mm=4cm wide, 5mm=0.5cm thick arms
    code = """
import adsk.core, adsk.fusion
rootComp = design.rootComponent
sketches = rootComp.sketches
sketch = sketches.add(rootComp.xYConstructionPlane)
lines = sketch.sketchCurves.sketchLines

# Draw L-shape profile (all dimensions in cm)
# L: 4cm x 4cm, arm thickness 0.5cm (5mm)
p1 = adsk.core.Point3D.create(0, 0, 0)
p2 = adsk.core.Point3D.create(4, 0, 0)
p3 = adsk.core.Point3D.create(4, 0.5, 0)
p4 = adsk.core.Point3D.create(0.5, 0.5, 0)
p5 = adsk.core.Point3D.create(0.5, 4, 0)
p6 = adsk.core.Point3D.create(0, 4, 0)

lines.addByTwoPoints(p1, p2)
lines.addByTwoPoints(p2, p3)
lines.addByTwoPoints(p3, p4)
lines.addByTwoPoints(p4, p5)
lines.addByTwoPoints(p5, p6)
lines.addByTwoPoints(p6, p1)

# Extrude the L-shape 5mm (0.5cm) thick
prof = sketch.profiles.item(0)
extrudes = rootComp.features.extrudeFeatures
extInput = extrudes.createInput(prof, adsk.fusion.FeatureOperations.NewBodyFeatureOperation)
extInput.setDistanceExtent(False, adsk.core.ValueInput.createByReal(0.5))
extrudes.add(extInput)
result['success'] = True
"""
    execute_script(code)

    print("\n  Expected violations:")
    print("    - CNC-001: Internal corner radius 0.0mm < 1.5mm (CRITICAL)")


# =============================================================================
# Part 4: Non-Standard Holes - Triggers GEN-001
# =============================================================================
def create_non_standard_holes():
    """80x80x10mm plate with 2x2 grid of 4.3mm holes (non-standard size)."""
    # 80mm=8cm, 10mm=1cm, 4.3mm=0.43cm, 30mm spacing=3cm
    print("\n  Step 1: Creating 80x80x10mm plate (8x8x1 cm)...")
    post("/Box", {"height": 8, "width": 8, "depth": 1, "x": 0, "y": 0, "z": 0})
    time.sleep(1)

    print("  Step 2: Adding 2x2 grid of 4.3mm diameter holes on TOP face...")
    # Points in cm, spaced 3cm (30mm) apart
    # faceindex 4 = top face for box on XY plane
    points = [
        [-1.5, -1.5], [-1.5, 1.5],
        [1.5, -1.5],  [1.5, 1.5],
    ]
    post("/holes", {
        "points": points,
        "width": 0.43,     # 4.3mm diameter in cm
        "depth": 1,         # through-all (1cm = 10mm = plate depth)
        "faceindex": 4,     # top face
    })

    print("\n  Expected violations:")
    print("    - GEN-001: Hole diameter 4.3mm not standard (SUGGESTION) x4")
    print("    - Nearest standard: 4.5mm")


# =============================================================================
# Part 5: Combined - Triggers ALL violation types
# =============================================================================
def create_combined():
    """60x60x40mm box with thin walls, small holes, non-standard holes, sharp corners."""
    # 60mm=6cm, 40mm=4cm
    print("\n  Step 1: Creating 60x60x40mm box (6x6x4 cm)...")
    post("/Box", {"height": 6, "width": 6, "depth": 4, "x": 0, "y": 0, "z": 0})
    time.sleep(1)

    print("  Step 2: Shelling to 1mm walls (0.1cm) -> triggers FDM-001...")
    post("/shell_body", {"thickness": 0.1, "faceindex": 0})
    time.sleep(2)

    # Add 2mm small holes on a side face (triggers FDM-003)
    print("  Step 3: Adding 2mm holes -> triggers FDM-003...")
    post("/holes", {
        "points": [[1, 1], [-1, -1]],
        "width": 0.2,       # 2mm diameter
        "depth": 0.1,       # through wall (1mm=0.1cm)
        "faceindex": 1,
    })
    time.sleep(1)

    # Add 4.3mm non-standard holes (triggers GEN-001)
    print("  Step 4: Adding 4.3mm holes -> triggers GEN-001...")
    post("/holes", {
        "points": [[-1, 1], [1, -1]],
        "width": 0.43,      # 4.3mm diameter
        "depth": 0.1,       # through wall
        "faceindex": 1,
    })

    # Internal corners from the shell are already sharp -> CNC-001

    print("\n  Expected violations:")
    print("    - FDM-001: Wall thickness 1mm < 2mm (CRITICAL)")
    print("    - FDM-003: Hole diameter 2mm < 3mm (WARNING) x2")
    print("    - GEN-001: Hole diameter 4.3mm not standard (SUGGESTION) x2")
    print("    - CNC-001: Sharp internal corners from shell (CRITICAL)")


# =============================================================================
# Part 6: Clean - Zero violations
# =============================================================================
def create_clean():
    """50x50x30mm box with 3mm walls, 5mm holes, 2mm fillets - no violations."""
    # 50mm=5cm, 30mm=3cm, 3mm=0.3cm, 5mm=0.5cm
    print("\n  Step 1: Creating 50x50x30mm box (5x5x3 cm)...")
    post("/Box", {"height": 5, "width": 5, "depth": 3, "x": 0, "y": 0, "z": 0})
    time.sleep(1)

    print("  Step 2: Shelling to 3mm walls (0.3cm) -> exceeds 2mm minimum...")
    post("/shell_body", {"thickness": 0.3, "faceindex": 0})
    time.sleep(1)

    print("  Step 3: Adding 5mm standard holes (0.5cm diameter)...")
    post("/holes", {
        "points": [[-1, -1], [-1, 1], [1, -1], [1, 1]],
        "width": 0.5,       # 5mm diameter
        "depth": 0.3,       # through wall (3mm=0.3cm)
        "faceindex": 1,
    })
    time.sleep(1)

    # Fillet internal edges
    print("  Step 4: Querying edges to find concave (internal) edges...")
    edges_data = get("/get_edges_info")
    edges = edges_data.get("edges", [])
    concave_indices = [e["index"] for e in edges if e.get("is_concave", False)]
    print(f"    Found {len(concave_indices)} concave edges: {concave_indices[:10]}...")

    if concave_indices:
        print("  Step 5: Adding 2mm fillets (0.2cm) to internal edges...")
        post("/fillet_specific_edges", {
            "edge_indices": concave_indices,
            "radius": 0.2,  # 2mm = 0.2cm
        })

    print("\n  Expected violations:")
    print("    - NONE! All rules satisfied. Green checkmark.")


# =============================================================================
# Main
# =============================================================================
PARTS = [
    ("test_thin_walls", create_thin_walls),
    ("test_small_holes", create_small_holes),
    ("test_sharp_corners", create_sharp_corners),
    ("test_non_standard_holes", create_non_standard_holes),
    ("test_combined", create_combined),
    ("test_clean", create_clean),
]


def main():
    if not health_check():
        sys.exit(1)

    # Allow running a specific part by number
    if len(sys.argv) > 1:
        part_num = int(sys.argv[1])
        if 1 <= part_num <= 6:
            name, builder = PARTS[part_num - 1]
            print(f"\n{'='*60}")
            print(f"  Building Part {part_num}: {name}")
            print(f"{'='*60}")
            clear()
            builder()
            wait_for_user(name)
            print("\nDone!")
            return
        else:
            print(f"Invalid part number: {part_num}. Use 1-6.")
            sys.exit(1)

    # Build all parts
    for i, (name, builder) in enumerate(PARTS, 1):
        print(f"\n{'='*60}")
        print(f"  Building Part {i}/6: {name}")
        print(f"{'='*60}")
        clear()
        builder()
        wait_for_user(name)

    print(f"\n{'='*60}")
    print("  All 6 test parts created!")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()
