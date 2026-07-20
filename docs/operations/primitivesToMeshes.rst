.. AUTO GENERATED FILE - DO NOT EDIT

====================
Primitives to Meshes
====================

**Key**: ``primitivesToMeshes``

This operation replaces gprim types sphere, cylinder, cone, and cube with a mesh approximation. This allows the geometry to be used with operations that require mesh types.

Arguments
---------

Primitives to convert
^^^^^^^^^^^^^^^^^^^^^

Optional list of prim paths to consider

    - Name: ``paths``
    - Type: ``[string]``
    - Default Value: ``[]``

Convert sphere primitives
^^^^^^^^^^^^^^^^^^^^^^^^^

Whether or not to generate meshes from sphere prims.

    - Name: ``convertSpheres``
    - Type: ``bool``
    - Default Value: ``True``

Longitude divisions
^^^^^^^^^^^^^^^^^^^

The number of longitudinal divisions in which to divide spheres.  Must be at least 3.

    - Name: ``sphereLongitudeDivisions``
    - Type: ``int``
    - Default Value: ``32``
    - Min Value: ``3.0``

Latitude divisions
^^^^^^^^^^^^^^^^^^

The number of latitudinal divisions in which to divide spheres.  Must be at least 2.

    - Name: ``sphereLatitudeDivisions``
    - Type: ``int``
    - Default Value: ``16``
    - Min Value: ``2.0``

Convert cylinder primitives
^^^^^^^^^^^^^^^^^^^^^^^^^^^

Whether or not to generate meshes from cylinder prims.

    - Name: ``convertCylinders``
    - Type: ``bool``
    - Default Value: ``True``

Wall divisions
^^^^^^^^^^^^^^

The number of divisions to make around the cylinder wall.  Must be at least 3.

    - Name: ``cylinderWallDivisions``
    - Type: ``int``
    - Default Value: ``32``
    - Min Value: ``3.0``

Length divisions
^^^^^^^^^^^^^^^^

The number of end-to-end divisions to make along the cylinder.  Must be positive.

    - Name: ``cylinderLatitudeDivisions``
    - Type: ``int``
    - Default Value: ``1``
    - Min Value: ``1.0``

Generate endcaps
^^^^^^^^^^^^^^^^

Whether or not to add endcaps to generated cylinder meshes.

    - Name: ``cylinderEndcaps``
    - Type: ``bool``
    - Default Value: ``True``

Convert cone primitives
^^^^^^^^^^^^^^^^^^^^^^^

Whether or not to generate meshes from cone prims.

    - Name: ``convertCones``
    - Type: ``bool``
    - Default Value: ``True``

Side divisions
^^^^^^^^^^^^^^

The number of divisions to make around the side of the cone.  Must be at least 3.

    - Name: ``coneSideDivisions``
    - Type: ``int``
    - Default Value: ``64``
    - Min Value: ``3.0``

Length divisions
^^^^^^^^^^^^^^^^

The number of divisions to make along the length of the cone.  Must be positive.

    - Name: ``coneLengthDivisions``
    - Type: ``int``
    - Default Value: ``3``
    - Min Value: ``1.0``

Generate bases
^^^^^^^^^^^^^^

Whether or not to add a base to generated cone meshes.

    - Name: ``coneBases``
    - Type: ``bool``
    - Default Value: ``True``

Convert cube primitives
^^^^^^^^^^^^^^^^^^^^^^^

Whether or not to generate meshes from cube prims.

    - Name: ``convertCubes``
    - Type: ``bool``
    - Default Value: ``True``

