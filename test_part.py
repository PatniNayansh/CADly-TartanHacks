"""
Cadly DFM Test Part Creator
Creates a test part in Fusion 360 with intentional manufacturing violations.

Expected violations:
  1. FDM-001: Wall thickness 1mm < 2mm minimum
  2. CNC-001: Sharp internal corners on pocket (no fillet)
  3. GEN-001: Hole diameter 2.8mm (nearest standard: 3.0mm)
  4. CNC-002: Hole depth:diameter ratio ~5.4:1 > 4:1 max

Usage: python test_part.py
Requires: Fusion 360 add-in running on http://localhost:5000
"""

import requests
import time
import json

FUSION_URL = "http://localhost:5000"
HEADERS = {"Content-Type": "application/json"}


def post(endpoint, data=None):
    """Send POST request to Fusion add-in."""
    url = f"{FUSION_URL}/{endpoint}"
    payload = json.dumps(data or {})
    resp = requests.post(url, data=payload, headers=HEADERS, timeout=15)
    result = resp.json()
    status = "OK" if resp.status_code == 200 else f"ERR {resp.status_code}"
    print(f"  [{status}] {endpoint}: {json.dumps(result)[:150]}")
    return result


def get(endpoint):
    """Send GET request to Fusion add-in."""
    url = f"{FUSION_URL}/{endpoint}"
    resp = requests.get(url, timeout=20)
    result = resp.json()
    print(f"  [OK] {endpoint}: {json.dumps(result)[:150]}")
    return result


def main():
    print("=" * 50)
    print("  Cadly DFM Test Part Creator")
    print("=" * 50)
    print()

    # Step 1: Test connection
    print("[0/6] Testing Fusion 360 connection...")
    try:
        post("test_connection")
    except Exception as e:
        print(f"  FAILED: Cannot connect to Fusion 360 at {FUSION_URL}")
        print(f"  Error: {e}")
        print("  Make sure the Fusion 360 add-in is running.")
        return
    print()

    # Step 1: Clear workspace
    print("[1/6] Clearing workspace...")
    post("delete_everything")
    time.sleep(1)
    print()

    # Step 2: Create base box 50x30x20mm
    # Fusion units: 1 unit = 1 cm. So 50mm = 5cm, 30mm = 3cm, 20mm = 2cm
    # Box center at origin. Box spans: x[-2.5, 2.5], y[-1.5, 1.5], z[-1, 1]
    print("[2/6] Creating base box (50 x 30 x 20 mm)...")
    post("Box", {
        "width": "5",      # 50mm in X direction
        "height": "3",     # 30mm in Y direction
        "depth": "2",      # 20mm in Z direction
        "x": 0.0,
        "y": 0.0,
        "z": 0.0,
        "Plane": "XY"
    })
    time.sleep(2)
    print()

    # Step 3: Draw a rectangle on the top face for the pocket cut
    # Top face is at z = 1.0 cm (half of 2cm depth)
    # Inset by 1mm (0.1cm) from each side to create 1mm thin walls
    # Inner rectangle: 48 x 28 mm = 4.8 x 2.8 cm
    # Corner 1: (-2.4, -1.4) Corner 2: (2.4, 1.4) at z=1.0
    print("[3/6] Drawing pocket rectangle on top face (1mm wall offset)...")
    post("draw_2d_rectangle", {
        "x_1": -2.4, "y_1": -1.4, "z_1": 1.0,
        "x_2":  2.4, "y_2":  1.4, "z_2": 1.0,
        "plane": "XY"
    })
    time.sleep(1)
    print()

    # Step 4: Cut extrude the pocket 19mm deep (leaves 1mm bottom wall)
    # 19mm = 1.9cm. This leaves 20mm - 19mm = 1mm bottom wall.
    # Negative depth = cut downward from the sketch plane
    print("[4/6] Cut extruding pocket (19mm deep -> 1mm bottom wall)...")
    post("cut_extrude", {"depth": -1.9})
    time.sleep(2)
    print()

    # Step 5: Draw a circle for a non-standard hole
    # 2.8mm diameter = 1.4mm radius = 0.14cm radius
    # Position: offset from center on the top face (z=1.0)
    # This violates GEN-001 (nearest standard drill: 3.0mm)
    print("[5/6] Drawing 2.8mm diameter hole on top face...")
    post("create_circle", {
        "radius": 0.14,    # 1.4mm = 0.14cm -> 2.8mm diameter
        "x": 1.5,          # 15mm from center
        "y": 0.0,
        "z": 1.0,          # top face
        "plane": "XY"
    })
    time.sleep(1)
    print()

    # Step 6: Cut extrude the hole 15mm deep
    # Depth:diameter ratio = 15mm / 2.8mm = 5.36 (violates CNC-002 max 4:1)
    print("[6/6] Cut extruding hole (15mm deep -> 5.4:1 depth ratio)...")
    post("cut_extrude", {"depth": -1.5})
    time.sleep(2)
    print()

    # Done - print summary
    print("=" * 50)
    print("  Test Part Created!")
    print("=" * 50)
    print()
    print("Expected DFM violations:")
    print("  1. FDM-001: Wall thickness 1.0mm (min 2.0mm for FDM)")
    print("  2. SLA-001: Wall thickness 1.0mm (min 1.0mm for SLA - borderline)")
    print("  3. CNC-001: Sharp internal corners on pocket (min 1.5mm radius)")
    print("  4. GEN-001: Hole diameter 2.8mm (nearest std: 3.0mm)")
    print("  5. CNC-002: Hole depth:diameter = 5.4:1 (max 4.0:1)")
    print()

    # Verify by querying body properties
    print("--- Verifying geometry ---")
    try:
        props = get("get_body_properties")
        if "bodies" in props and props["bodies"]:
            body = props["bodies"][0]
            print(f"  Name:    {body['name']}")
            print(f"  Volume:  {body['volume_cm3']:.4f} cm3")
            print(f"  Area:    {body['area_cm2']:.4f} cm2")
            print(f"  Faces:   {body['face_count']}")
            print(f"  Edges:   {body['edge_count']}")
            bb = body.get("bounding_box", {})
            if bb:
                dims_mm = [
                    round((bb["max"][i] - bb["min"][i]) * 10, 1)
                    for i in range(3)
                ]
                print(f"  Size:    {dims_mm[0]} x {dims_mm[1]} x {dims_mm[2]} mm")
        else:
            print("  WARNING: No bodies found!")
    except Exception as e:
        print(f"  Could not verify: {e}")

    print()
    print("Run DFM analysis: python -m uvicorn src.main:app --port 3000")
    print("Then open: http://localhost:3000")


if __name__ == "__main__":
    main()
