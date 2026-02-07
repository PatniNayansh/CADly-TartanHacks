# Fusion 360 Scripting Lessons Learned

## OVERRIDES
These are general lessons. If a specific situation contradicts a lesson below, trust the specific situation. Update this file when new lessons are learned.

---

## 1. Cut Extrude Direction

**Problem:** Cut extrude kept failing with "No target body found to cut or intersect!" even when the sketch was clearly on a body face.

**Root cause:** When you sketch on a face, the default extrude direction follows the face normal (pointing outward, away from material). A cut in that direction goes into empty space, not into the body.

**Lesson:** Always think about which direction the face normal points. For a cut to go INTO the body, you often need the opposite of the face normal direction. Use `setOneSideExtent(distDef, ExtentDirections.NegativeExtentDirection)` when the face normal points away from material.

**Gotcha:** Even flipping to NegativeExtentDirection can fail on very thin walls (e.g., 1mm shell walls) — the cut may not register. When in doubt, use `setAllExtent()` from a construction plane instead of cutting from a face.

---

## 2. Sketch Profiles — Multiple Profiles Exist

**Problem:** Drawing a rectangle inside a face boundary creates TWO profiles, not one. `profiles.item(0)` may select the wrong one.

**Root cause:** When a sketch has a closed shape drawn on a face, Fusion creates profiles for every enclosed region. A rectangle inside a face boundary creates: (a) the inner rectangle area, and (b) the outer ring between the rectangle and the face edge.

**Lesson:** After drawing a sketch, always check `sketch.profiles.count`. If there are multiple profiles, identify the correct one by area (`p.areaProperties().area`) or by iterating and comparing. Never blindly use `profiles.item(0)`.

---

## 3. Shell vs. Pocket for Thin Walls

**Problem:** Manually creating a pocket with a rectangle sketch and cut extrude was unreliable — direction issues, profile selection issues, and the cut sometimes went all the way through.

**What works:** `shellFeatures` is the reliable way to create uniform thin walls. Create a solid body first, then shell it by removing one face. Shell handles wall thickness, internal geometry, and face creation correctly in one operation.

**Lesson:** For test parts that need thin walls, prefer `shellFeatures` over manual pocket cuts. Shell takes a face collection (faces to remove) and a thickness value. It's one API call vs. multiple error-prone steps.

---

## 4. Hole Creation — Sketch on Construction Plane, Not on Body Faces

**Problem:** Sketching circles on body faces (especially thin shell walls) and cutting failed repeatedly because the cut direction never found the body.

**What works:** Sketch the circle on a construction plane (e.g., `rootComp.xYConstructionPlane`) at a known Z position, then use `setAllExtent(PositiveExtentDirection)` to cut through whatever body is in the way.

**Lesson:** For through-holes, always prefer construction planes + `setAllExtent()` over sketching on body faces + distance extent. It's more reliable because it doesn't depend on face normals or body thickness.

---

## 5. Unit System

**Rule:** Fusion 360 internal units are CENTIMETERS. All API values for distances, radii, positions are in cm.
- 1mm = 0.1cm
- 2mm diameter hole = 0.1cm radius
- 50mm = 5.0cm

**Lesson:** Always convert mm to cm before passing values to the API. Double-check by thinking: "Does this number make sense in centimeters?"

---

## 6. The `cut_extrude` Add-in Endpoint

**How it works:** The `/cut_extrude` endpoint grabs the LAST sketch (`sketches.item(sketches.count - 1)`) and uses `profiles.item(0)`. It always cuts in the default direction with a simple distance.

**Limitation:** It doesn't let you choose which profile, which direction, or which body. For anything non-trivial, use `/execute_script` instead.

**Lesson:** Use the simple endpoints (`/Box`, `/cut_extrude`) only for the simplest cases. For test parts or complex geometry, use `/execute_script` with full Fusion API control.

---

## 7. Order of Operations for Test Parts

**Reliable pattern:**
1. Create base solid (box, cylinder) using `NewBodyFeatureOperation`
2. Apply subtractive features (shell, pockets, holes)
3. Shell BEFORE adding holes (shell changes face indices)
4. For holes, sketch on construction planes, not body faces
5. Use `setAllExtent()` for through-features

**Unreliable pattern:**
1. Creating sketches on body faces for cuts (direction ambiguity)
2. Using distance extent on thin walls (may not find body)
3. Multiple separate cut operations on the same face (profile confusion)

---

## 8. Debugging Fusion Scripts

- Use `result["debug_key"] = value` inside execute_script to return diagnostic info
- Check `sketch.profiles.count` and area of each profile before extruding
- Use `/get_faces_info` to inspect face normals and centroids after operations
- Use `/get_body_properties` to check body count (unexpected splits = something went wrong)
- If body count increases unexpectedly, a cut created a separate body instead of modifying the existing one

---

## 9. Face Normals After Shell

**Gotcha:** After shelling a body, face normals may not be what you expect. The outer bottom face of a shelled box has normal [0,0,1] (pointing up, away from exterior), NOT [0,0,-1]. Always verify with `/get_faces_info` rather than assuming.

---

## 10. Profile Selection by Area

**Reliable pattern for selecting profiles:**
```python
# For the inner/smaller region:
smallest = min(range(sketch.profiles.count),
               key=lambda i: sketch.profiles.item(i).areaProperties().area)
prof = sketch.profiles.item(smallest)

# For the outer/larger region:
largest = max(range(sketch.profiles.count),
              key=lambda i: sketch.profiles.item(i).areaProperties().area)
prof = sketch.profiles.item(largest)
```

Never hardcode profile indices — they depend on sketch geometry and can vary.

---

## 11. Wall Detection: Parallel Normals, NOT Anti-Parallel

**Problem:** Wall detection algorithm looked for anti-parallel face pairs (normals pointing in opposite directions, dot ≈ -1) and returned 28-50mm thicknesses instead of the actual 1mm shell walls.

**Root cause:** `face.geometry.normal` returns the **mathematical plane normal**, NOT the B-Rep outward-facing normal. In a shelled body, the inner and outer faces of the same wall lie on parallel planes, so they have the **same** `.geometry.normal` direction.

For example, a shelled box's front wall:
- Outer face at Y=0.0: `geometry.normal` = (0, -1, 0)
- Inner face at Y=0.1: `geometry.normal` = (0, -1, 0) — SAME direction!

Anti-parallel pairs (dot ≈ -1) match faces on **opposite sides** of the body (e.g., front vs back), giving huge distances.

**Lesson:** To detect wall thickness, look for **parallel** face pairs (dot ≈ +1) that are close together. Use the "closest parallel partner per face" pattern. Best done server-side from `/get_faces_info` data rather than in the Fusion add-in (avoids restart cycles).

**Verified data (shelled 50×30×20mm box, 1mm walls):**
```
Face 1: normal (0,+1,0), Y=2.9 (inner back)  ←→ Face 6: normal (0,+1,0), Y=3.0 (outer back)  = 1mm ✓
Face 3: normal (0,-1,0), Y=0.1 (inner front)  ←→ Face 8: normal (0,-1,0), Y=0.0 (outer front)  = 1mm ✓
Face 5: normal (0,0,+1), Z=0.1 (inner bottom) ←→ Face 11: normal (0,0,+1), Z=0.0 (outer bottom) = 1mm ✓
```

---

## 12. Shell CreateInput Requires ObjectCollection

**Problem:** `shellFeatures.createInput([face])` fails with a type error.

**Root cause:** The Fusion API expects an `adsk.core.ObjectCollection`, not a Python list.

**Fix:**
```python
faces_to_remove = adsk.core.ObjectCollection.create()
faces_to_remove.add(top_face)
shell_input = shells.createInput(faces_to_remove)
```

---

## 13. Fillet Radius Must Be Less Than Wall Thickness

**Problem:** Applying a 1.5mm fillet to 1mm shell walls destroyed geometry — walls deleted, faces corrupted.

**Root cause:** Fusion allows the fillet operation to proceed even when the radius is too large for the geometry, but the result is invalid topology (missing faces, split bodies).

**Lesson:** Before applying fillets, query wall thickness and cap the fillet radius to < 50% of the minimum wall thickness. Our code uses 40% as a safety margin.

---

## 14. Fusion Add-in HTTP Methods: GET for Queries, POST for Mutations

**Problem:** Fix validation called `analyze_holes` via POST, got 404 (the add-in only serves it on GET), failed validation 3 times, then rolled back a perfectly good fix.

**Root cause:** The add-in's `do_GET` handles query endpoints (`get_body_properties`, `get_faces_info`, `get_edges_info`, `analyze_walls`, `analyze_holes`). `do_POST` handles mutations (`execute_script`, `fillet_specific_edges`, `set_parameter`, etc).

**Lesson:** Always use GET for read-only geometry queries, POST only for mutations. In the FusionClient, use `client.get("endpoint")` not `client.post("endpoint")` for queries.

---

## 15. Hole Depth Detection — Use Bounding Box, Not Edge Projections

**Problem:** `_analyze_holes()` returned 0mm or 1mm depth for blind holes, breaking CNC-003 (depth ratio) detection.

**Root cause:** The old approach projected circular edge centers onto the cylinder axis and took `max - min`. Blind holes only have ONE circular edge (at the top rim), so `len(edge_projections) < 2` and depth defaulted to 0.

**Fix:** Use `face.boundingBox` to measure the cylindrical face's extent along its axis. Project all 8 bounding box corners onto the cylinder axis direction and take `max - min`.

```python
bbox = face.boundingBox
corners = [
    (bbox.minPoint.x, bbox.minPoint.y, bbox.minPoint.z),
    (bbox.maxPoint.x, bbox.minPoint.y, bbox.minPoint.z),
    # ... all 8 combinations
    (bbox.maxPoint.x, bbox.maxPoint.y, bbox.maxPoint.z),
]
projections = [c[0]*axis.x + c[1]*axis.y + c[2]*axis.z for c in corners]
depth_cm = max(projections) - min(projections)
```

**Lesson:** `face.boundingBox` is a reliable way to measure a face's spatial extent. Edge-based methods fail when the face has fewer edges than expected (blind holes, partial cylinders).

**Note:** On shelled parts, a through-hole's cylindrical face only spans the shell wall thickness (e.g., 1mm). This is correct — the cylinder only exists where there's material.

---

## 16. Wall Fix — Shell Parts Need Different Strategy

**Problem:** `wall_fix.py` only searched `extrudeFeatures` for cut operations. Shell parts use `shellFeatures`, so the fix found nothing and returned failure.

**Fix:** Add a second strategy: after the extrude loop fails, iterate `rootComp.features.shellFeatures` and adjust `shell.insideThickness.value` to the target thickness.

```python
# Strategy 1: cut-extrude depth (for pocket-based thin walls)
# Strategy 2: shell thickness (for shelled parts)
if not fixed:
    shells = rootComp.features.shellFeatures
    for si in range(shells.count):
        shell = shells.item(si)
        shell.insideThickness.value = target_cm
```

**Lesson:** Always consider multiple feature types that could create thin walls. Cut-extrude and shell are the two most common. Check for both before giving up.

---

## 17. participantBodies for Multi-Body Cut Operations

**Problem:** `"No target body found to cut or intersect!"` when cutting a hole into a second body, even when the sketch was correctly positioned.

**Root cause:** When multiple bodies exist, Fusion doesn't automatically know which body to cut. The extrude targets the "default" body, which might not be the one you want.

**Fix:** Set `input.participantBodies` to explicitly specify which body to cut:
```python
input = ext.createInput(prof, FeatureOperations.CutFeatureOperation)
input.setDistanceExtent(False, ValueInput.createByReal(depth))
input.participantBodies = [rootComp.bRepBodies.item(target_index)]
ext.add(input)
```

**Lesson:** In multi-body documents, always set `participantBodies` for cut operations. Otherwise Fusion picks the default body, which may not be the intended target.

---

## 18. Undo is Fire-and-Forget — Wait Before Querying

**Problem:** After calling `/undo`, immediately querying geometry still returned old state.

**Root cause:** The add-in's `/undo` endpoint puts the undo command on `task_queue` and returns immediately. The actual undo happens asynchronously in the main thread event handler.

**Lesson:** After POST to `/undo`, wait 1-2 seconds before querying geometry. The undo is not synchronous — unlike `/execute_script` which uses a query event to wait for completion, `/undo` is fire-and-forget.

---

## 19. Fillet Validation — Check Arc Radius, Not Just Edge Count

**Problem:** Corner fix validation only checked `len(edges_after) != len(edges_before)`. This passed even when the fillet was undersized (capped by wall thickness).

**Fix:** Validate by looking for new arc/circle edges at the expected radius:
```python
new_arcs = [
    e for e in edges_after
    if e.get("type") in ("arc", "circle")
    and abs((e.get("radius_cm", 0) * 10) - target_mm) < 0.5
]
return len(new_arcs) > 0
```

**Lesson:** Edge count changes prove *something* happened, but not *what* happened. For fillets, verify the actual radius of new arc edges matches the intended radius.
