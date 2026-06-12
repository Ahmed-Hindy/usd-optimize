.. AUTO GENERATED FILE - DO NOT EDIT

===============
Decimate Meshes
===============

**Key**: ``decimateMeshes``

Reduce decimation amount on an input ``UsdGeom`` mesh primitive type.

Arguments
---------

Meshes to Decimate
^^^^^^^^^^^^^^^^^^

Optional list of prim paths/expressions to decimate

    - Name: ``paths``
    - Type: ``[string]``
    - Default Value: ``[]``

Reduce to Percentage
^^^^^^^^^^^^^^^^^^^^

Reduce to end result percentage from original vertex count, 0.0-100.0 values accepted. Set to 0 if using Maximum Mean Error.

    - Name: ``reductionFactor``
    - Type: ``float``
    - Default Value: ``50``
    - Min Value: ``0.0``
    - Max Value: ``100.0``

Maximum Mean Error
^^^^^^^^^^^^^^^^^^

Maximum mean error for the decimation, 0.0-100.0 values accepted. Set 0 to disable this option.

    - Name: ``maxMeanError``
    - Type: ``float``
    - Default Value: ``0``
    - Min Value: ``0.0``
    - Max Value: ``10.0``

Guide Decimation
^^^^^^^^^^^^^^^^

Guide Decimation by using Normals or Colors (if available)

    - Name: ``guideDecimation``
    - Type: ``int``
    - Default Value: ``0``
    - Enum Values:
        - ``0: By normals``
        - ``1: By colors``
        - ``2: Off``

Pin mesh boundaries
^^^^^^^^^^^^^^^^^^^

Preserve the mesh boundaries

    - Name: ``pinBoundaries``
    - Type: ``bool``
    - Default Value: ``False``

Topology Simplification
^^^^^^^^^^^^^^^^^^^^^^^

Allow changes to mesh topology when decimating. Note that this will take more time

    - Name: ``allowCutAndGlue``
    - Type: ``bool``
    - Default Value: ``False``

CPU Vertex Threshold
^^^^^^^^^^^^^^^^^^^^

Use CPU Parallel algorithm if vertex count is greater than this value

    - Name: ``cpuVertexCountThreshold``
    - Type: ``int``
    - Default Value: ``100000``
    - Min Value: ``0.0``

GPU Vertex Threshold
^^^^^^^^^^^^^^^^^^^^

Use GPU algorithm if vertex count is greater than this value

    - Name: ``gpuVertexCountThreshold``
    - Type: ``int``
    - Default Value: ``500000``
    - Min Value: ``0.0``

