.. AUTO GENERATED FILE - DO NOT EDIT

====================
Find Occluded Meshes
====================

**Key**: ``findOccludedMeshes``

Finds meshes that are globally occluded meaning they are occluded from any camera that does not cross meshes in the scene.

Arguments
---------

Meshes used for occlusion testing
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Meshes that are tested for occlusion as well as considered as occluders

    - Name: ``paths``
    - Type: ``[string]``
    - Default Value: ``[]``

Clustered
^^^^^^^^^

Split the stage into clusters of meshes with overlapping bounding boxes and check visibility per cluster, improving both accuracy and performance by reducing the number of meshes compared at the same time

    - Name: ``clustered``
    - Type: ``bool``
    - Default Value: ``True``

Minimum gap size
^^^^^^^^^^^^^^^^

The minimum gap size corresponding to the spacing of the background grid. Gaps smaller than this value are considered closed for occlusion culling. The actual grid spacing is max(minimumGapSize, maxDim/maximumGridResolution). Very small values defer to maximumGridResolution for spacing, producing a finer grid that detects smaller gaps and results in fewer meshes being flagged as occluded. It is essentially a tolerance for how sealed an enclosure needs to be: e.g. a value of 3.5 means ignore any opening smaller than 3.5 scene units when deciding if something is hidden

    - Name: ``minimumGapSize``
    - Type: ``float``
    - Default Value: ``0.01``
    - Min Value: ``0.0``

Maximum grid resolution
^^^^^^^^^^^^^^^^^^^^^^^

The maximum number of cells along the longest axis of the grid used for visibility checking. This caps the grid resolution to prevent excessive memory and compute costs (the grid is 3D, so memory scales with the cube of resolution). A value of 500 is suitable for powerful GPUs, use smaller values for less powerful GPUs or CPUs

    - Name: ``maximumGridResolution``
    - Type: ``float``
    - Default Value: ``500``
    - Min Value: ``1.0``

Check Transparency
^^^^^^^^^^^^^^^^^^

Exclude meshes with opacity < 1.0 from occlusion testing

    - Name: ``checkTransparency``
    - Type: ``bool``
    - Default Value: ``False``

Action
^^^^^^

What to do with occluded meshes

    - Name: ``action``
    - Type: ``int``
    - Default Value: ``3``
    - Enum Values:
        - ``1: Delete``
        - ``2: Deactivate``
        - ``3: Hide``

