"""Test connection to the Fusion 360 add-in and print geometry info.

Usage: python -m scripts.test_mcp
       (or run directly: python scripts/test_mcp.py)

Requires Fusion 360 to be running with the MCP add-in loaded on port 5000.
"""

import asyncio
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.fusion.client import FusionClient, FusionConnectionError
from src.fusion.geometry import GeometryHelper


async def main():
    client = FusionClient()

    print("=" * 60)
    print("Cadly v2 - Fusion 360 Connection Test")
    print("=" * 60)

    # Health check
    print("\n[1] Testing connection...")
    connected = await client.health_check()
    if not connected:
        print("  FAILED: Cannot reach Fusion 360 add-in at http://localhost:5000")
        print("  Make sure Fusion 360 is running with the MCP add-in loaded.")
        await client.close()
        return

    print("  OK: Connected to Fusion 360 add-in")

    # Geometry queries
    geo = GeometryHelper(client)

    print("\n[2] Querying body properties...")
    try:
        bodies = await geo.get_bodies()
        if not bodies:
            print("  WARNING: No bodies found. Open a part in Fusion 360 first.")
        else:
            body = bodies[0]
            print(f"  Body: {body.name}")
            print(f"  Volume: {body.volume_cm3:.4f} cm3")
            print(f"  Area: {body.area_cm2:.4f} cm2")
            print(f"  Faces: {body.face_count}")
            print(f"  Edges: {body.edge_count}")
            if body.bounding_box:
                bb = body.bounding_box
                print(f"  Bounding box: {bb.get('min')} -> {bb.get('max')}")
    except Exception as e:
        print(f"  ERROR: {e}")

    print("\n[3] Querying faces...")
    try:
        faces = await geo.get_faces()
        print(f"  Found {len(faces)} faces")
        for f in faces[:5]:
            print(f"    Face {f.index}: {f.face_type}, area={f.area_cm2:.4f} cm2")
        if len(faces) > 5:
            print(f"    ... and {len(faces) - 5} more")
    except Exception as e:
        print(f"  ERROR: {e}")

    print("\n[4] Querying edges...")
    try:
        edges = await geo.get_edges()
        concave = [e for e in edges if e.is_concave]
        print(f"  Found {len(edges)} edges ({len(concave)} concave/internal)")
        for e in edges[:5]:
            extra = " [CONCAVE]" if e.is_concave else ""
            print(f"    Edge {e.index}: {e.edge_type}, len={e.length_cm:.4f} cm{extra}")
        if len(edges) > 5:
            print(f"    ... and {len(edges) - 5} more")
    except Exception as e:
        print(f"  ERROR: {e}")

    print("\n[5] Analyzing walls...")
    try:
        walls = await geo.get_walls()
        print(f"  Found {len(walls)} wall pairs")
        for w in walls:
            print(f"    Faces {w.face_index_1}-{w.face_index_2}: {w.thickness_mm:.2f} mm")
    except Exception as e:
        print(f"  ERROR: {e}")

    print("\n[6] Analyzing holes...")
    try:
        holes = await geo.get_holes()
        print(f"  Found {len(holes)} holes")
        for h in holes:
            print(f"    Face {h.face_index}: dia={h.diameter_mm:.2f} mm, depth={h.depth_mm:.2f} mm, ratio={h.depth_to_diameter_ratio:.1f}")
    except Exception as e:
        print(f"  ERROR: {e}")

    print("\n" + "=" * 60)
    print("Connection test complete.")
    print("=" * 60)

    await client.close()


if __name__ == "__main__":
    asyncio.run(main())
