.. AUTO GENERATED FILE - DO NOT EDIT

========
Box Clip
========

**Key**: ``boxClip``

Clips meshes to a user defined axis-aligned box, with options for keeping geometry inside or outside the box and handling partial intersections.

Arguments
---------

Meshes To Process
^^^^^^^^^^^^^^^^^

Optional list of prim paths to consider

    - Name: ``paths``
    - Type: ``[string]``
    - Default Value: ``[]``

Clip Box Definition
^^^^^^^^^^^^^^^^^^^

How the clip box is defined

    - Name: ``clipBoxDef``
    - Type: ``int``
    - Default Value: ``1``
    - Enum Values:
        - ``0: Corners of Box``
        - ``1: Prim``

min x
^^^^^

Min x value

    - Name: ``minX``
    - Type: ``float``
    - Default Value: ``0``

min y
^^^^^

Min y value

    - Name: ``minY``
    - Type: ``float``
    - Default Value: ``0``

min z
^^^^^

Min z value

    - Name: ``minZ``
    - Type: ``float``
    - Default Value: ``0``

max x
^^^^^

Max x value

    - Name: ``maxX``
    - Type: ``float``
    - Default Value: ``0``

max y
^^^^^

Max y value

    - Name: ``maxY``
    - Type: ``float``
    - Default Value: ``0``

max z
^^^^^

Max z value

    - Name: ``maxZ``
    - Type: ``float``
    - Default Value: ``0``

Clip Box Prim
^^^^^^^^^^^^^

Prim whose extents defines the clip box

    - Name: ``clipBoxPrimPath``
    - Type: ``str``
    - Default Value: ``""``

Ignore Clip Box Side
^^^^^^^^^^^^^^^^^^^^

Optionally ignore one side of the clip box (extending it to infinity)

    - Name: ``ignoreClipBoxSide``
    - Type: ``int``
    - Default Value: ``0``
    - Enum Values:
        - ``0: None``
        - ``1: -X``
        - ``2: +X``
        - ``3: -Y``
        - ``4: +Y``
        - ``5: -Z``
        - ``6: +Z``

Clip Mode
^^^^^^^^^

How geometry is clipped relative to the box

    - Name: ``clipMode``
    - Type: ``int``
    - Default Value: ``0``
    - Enum Values:
        - ``0: Keep if fully inside clip box + keep if partially inside``
        - ``1: Keep if fully inside clip box + cut if partially inside``
        - ``2: Keep if fully inside clip box + discard if partially inside``
        - ``3: Keep if fully outside clip box + keep if partially outside``
        - ``4: Keep if fully outside clip box + discard if partially outside``

