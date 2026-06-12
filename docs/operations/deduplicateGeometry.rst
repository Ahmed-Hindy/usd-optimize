.. AUTO GENERATED FILE - DO NOT EDIT

====================
Deduplicate Geometry
====================

**Key**: ``deduplicateGeometry``

This will replace multiple duplicate geometric prims in a scene to a single prim and create references/instances to the single prim. Since a referenced prim uses less memory than the full duplicated prim, this option can reduce system memory and vram consumption.

This process is only effective if there are prims that are identical but are not already instanced; however, you may find this optimization may not have any effect on your scene.

The operation also supports a fuzzy comparison mode. In this mode, the similarity measure used is independent of the tessellation of meshes and based on their relative shape deviation. The fuzzy mode comparison is available as a CPU and GPU implementation.

This process supports deduplicating point-based geometry (meshes, basis curves, etc.). Note that in fuzzy mode, currently only meshes are supported for deduplication.

Arguments
---------

Geometry to De-duplicate
^^^^^^^^^^^^^^^^^^^^^^^^

Optional list of prim paths to consider

    - Name: ``meshPrimPaths``
    - Type: ``[string]``
    - Default Value: ``[]``

Tolerance
^^^^^^^^^

Acceptable point position change during deduplication. The value is a stage unit in worldspace

    - Name: ``tolerance``
    - Type: ``float``
    - Default Value: ``0.001``

Method
^^^^^^

Method used to conform meshes that are duplicates

    - Name: ``duplicateMethod``
    - Type: ``int``
    - Default Value: ``2``
    - Enum Values:
        - ``0: Copy Values``
        - ``1: Reference``
        - ``2: Instanceable Reference``
        - ``3: Set Attribute``
        - ``4: Point Instancer``

Point Instancer Location
^^^^^^^^^^^^^^^^^^^^^^^^

Where to author the PointInstancer for each duplicate set

    - Name: ``pointInstancerLocation``
    - Type: ``int``
    - Default Value: ``0``
    - Enum Values:
        - ``0: Common Root``
        - ``1: Custom Path``

Parent Path
^^^^^^^^^^^

Prim path to author the PointInstancer under. Created as an Xform if it does not exist.

    - Name: ``pointInstancerParentPath``
    - Type: ``str``
    - Default Value: ``""``

Minimum Duplicates
^^^^^^^^^^^^^^^^^^

Minimum number of duplicates a set must contain for a PointInstancer to be created. Sets with fewer duplicates are left untouched.

    - Name: ``minimumDuplicates``
    - Type: ``int``
    - Default Value: ``2``
    - Min Value: ``2.0``

Ignore Attributes
^^^^^^^^^^^^^^^^^

Optional list of attributes to ignore. This list can be explicit attributes, or if ending with a ':' can ignore namespaces.

    - Name: ``ignoreAttributes``
    - Type: ``[string]``
    - Default Value: ``[]``

Fuzzy mode
^^^^^^^^^^

When enabled, uses shape comparison to find duplicates that differ in tessellation or have baked-in point offsets

    - Name: ``fuzzy``
    - Type: ``bool``
    - Default Value: ``False``

Allow Scaling
^^^^^^^^^^^^^

When enabled, fuzzy comparison will factor out uniform scaling

    - Name: ``allowScaling``
    - Type: ``bool``
    - Default Value: ``False``

Consider Deep Transforms
^^^^^^^^^^^^^^^^^^^^^^^^

Look for duplicates where the points values have been uniformly transformed

    - Name: ``considerDeepTransforms``
    - Type: ``bool``
    - Default Value: ``True``

