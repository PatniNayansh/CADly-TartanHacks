"""
Fusion 360 Script: Create a part with intentional DFM violations
Copy and paste this into Fusion 360's Scripts and Add-Ins window
"""

import adsk.core
import adsk.fusion
import traceback

def run(context):
    ui = None
    try:
        app = adsk.core.Application.get()
        ui = app.userInterface
        design = app.activeProduct

        # Get the root component
        rootComp = design.rootComponent

        # Create a new sketch on the XY plane
        sketches = rootComp.sketches
        xyPlane = rootComp.xYConstructionPlane
        sketch = sketches.add(xyPlane)

        # Draw a rectangle (50mm x 30mm)
        lines = sketch.sketchCurves.sketchLines
        rect = lines.addTwoPointRectangle(
            adsk.core.Point3D.create(0, 0, 0),
            adsk.core.Point3D.create(5, 3, 0)  # 50mm x 30mm (cm units)
        )

        # Extrude the rectangle with THIN WALLS (1mm = 0.1cm)
        extrudes = rootComp.features.extrudeFeatures
        prof = sketch.profiles.item(0)

        extInput = extrudes.createInput(prof, adsk.fusion.FeatureOperations.NewBodyFeatureOperation)
        distance = adsk.core.ValueInput.createByReal(2)  # 20mm height
        extInput.setDistanceExtent(False, distance)

        # Shell to create thin walls (1mm = 0.1cm)
        baseBody = extrudes.add(extInput)

        # Add shell feature for thin walls
        shellFeatures = rootComp.features.shellFeatures
        shellInput = shellFeatures.createInput(baseBody.bodies.item(0))
        shellInput.insideThickness = adsk.core.ValueInput.createByReal(0.1)  # 1mm thin wall
        shell = shellFeatures.add(shellInput)

        # Add small holes (2mm diameter - too small)
        # Create sketch on top face
        topFace = baseBody.bodies.item(0).faces.item(0)
        holeSketch = sketches.add(topFace)
        circles = holeSketch.sketchCurves.sketchCircles

        # Add 3 small holes
        circles.addByCenterRadius(adsk.core.Point3D.create(1, 1, 0), 0.1)  # 2mm diameter
        circles.addByCenterRadius(adsk.core.Point3D.create(2.5, 1.5, 0), 0.1)
        circles.addByCenterRadius(adsk.core.Point3D.create(4, 1, 0), 0.1)

        # Extrude holes through
        for i in range(holeSketch.profiles.count):
            prof = holeSketch.profiles.item(i)
            holeInput = extrudes.createInput(prof, adsk.fusion.FeatureOperations.CutFeatureOperation)
            holeInput.setAllExtent(adsk.fusion.ExtentDirections.PositiveExtentDirection)
            extrudes.add(holeInput)

        # Add internal pocket with SHARP CORNERS (0mm radius)
        pocketSketch = sketches.add(topFace)
        pocketLines = pocketSketch.sketchCurves.sketchLines

        # Draw small rectangle inside (sharp corners)
        pocketRect = pocketLines.addTwoPointRectangle(
            adsk.core.Point3D.create(1.5, 0.5, 0),
            adsk.core.Point3D.create(3.5, 2.5, 0)
        )

        # Extrude pocket (cut)
        pocketProf = pocketSketch.profiles.item(0)
        pocketInput = extrudes.createInput(pocketProf, adsk.fusion.FeatureOperations.CutFeatureOperation)
        pocketDepth = adsk.core.ValueInput.createByReal(0.5)  # 5mm deep pocket
        pocketInput.setDistanceExtent(False, pocketDepth)
        extrudes.add(pocketInput)

        # Add steep overhang (60 degree angle)
        sideFace = None
        for face in baseBody.bodies.item(0).faces:
            if face.geometry.surfaceType == adsk.core.SurfaceTypes.PlaneSurfaceType:
                normal = face.geometry.normal
                if abs(normal.x) > 0.9:  # Side face
                    sideFace = face
                    break

        if sideFace:
            overhangSketch = sketches.add(sideFace)
            overhangLines = overhangSketch.sketchCurves.sketchLines

            # Draw triangle for overhang
            p1 = adsk.core.Point3D.create(0, 0.5, 0)
            p2 = adsk.core.Point3D.create(0, 1.5, 0)
            p3 = adsk.core.Point3D.create(0.866, 1, 0)  # 60 degree angle

            overhangLines.addByTwoPoints(p1, p2)
            overhangLines.addByTwoPoints(p2, p3)
            overhangLines.addByTwoPoints(p3, p1)

            # Extrude overhang
            overhangProf = overhangSketch.profiles.item(0)
            overhangInput = extrudes.createInput(overhangProf, adsk.fusion.FeatureOperations.JoinFeatureOperation)
            overhangDist = adsk.core.ValueInput.createByReal(1)
            overhangInput.setDistanceExtent(False, overhangDist)
            extrudes.add(overhangInput)

        ui.messageBox('✅ Bad part created!\n\nViolations:\n• Thin walls (1mm)\n• Small holes (2mm)\n• Sharp corners (0mm radius)\n• Steep overhang (60°)')

    except:
        if ui:
            ui.messageBox('Failed:\n{}'.format(traceback.format_exc()))

def stop(context):
    pass
