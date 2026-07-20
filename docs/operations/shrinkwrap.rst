.. AUTO GENERATED FILE - DO NOT EDIT

==========
Shrinkwrap
==========

**Key**: ``shrinkwrap``

This operation converts meshes to a level set volume using
`OpenVDB <https://www.openvdb.org/>`_ and extracts a watertight mesh back out. It is useful for closing
holes, simplifying topology, and creating LOD meshes. The algorithm rasterizes the input mesh into a
narrow-band level set, optionally erodes the surface to close gaps and holes, and extracts a new polygon
mesh from the resulting volume. The output mesh is written as a new sibling prim alongside the original,
which is preserved.

Choosing resolution
-------------------

``voxelSize`` is the dominant control and should be set first. It is the edge length of a level-set voxel,
in **stage units**: smaller values capture finer detail but cost cubically more memory and time, larger
values smooth the result and close bigger gaps. ``adaptivity`` (0-1) then simplifies flat regions of the
extracted mesh to reduce triangle count without re-running the volume step.

Scale and units
---------------

``voxelSize``, ``erode``, and ``threshold`` are all in stage units, so the right values depend on the
stage's ``metersPerUnit``. A scene authored in centimetres (``metersPerUnit`` = 0.01) needs voxel sizes
roughly 100x those of a scene authored in metres for the same physical resolution.

Tuning order
------------

1. Set ``voxelSize`` for the target detail level (start small and increase until cost is acceptable).
2. Increase ``erode`` to close larger gaps and holes.
3. Adjust ``threshold`` to shift the extracted iso-surface inward or outward.
4. Raise ``adaptivity`` to thin out triangles on flat areas.

Recommended pipelines
---------------------

Often run after ``merge`` so a group of parts becomes one watertight shell; target the merged prims with
``paths``. Pairs well with ``decimateMeshes`` afterward for LOD generation.

Starting configurations
-----------------------

Conservative detail preservation:

.. code-block:: json

    [{"operation": "shrinkwrap", "voxelSize": 0.05, "erode": 8.0}]

Gap-closing / hole-filling (coarser, more erosion):

.. code-block:: json

    [{"operation": "shrinkwrap", "voxelSize": 0.2, "erode": 16.0, "adaptivity": 0.5}]


Arguments
---------

Meshes to Shrinkwrap
^^^^^^^^^^^^^^^^^^^^

Optional list of prim paths/expressions to shrinkwrap

    - Name: ``paths``
    - Type: ``[string]``
    - Default Value: ``[]``

Voxel Size
^^^^^^^^^^

Explicit voxel size. Smaller values produce finer detail but use more memory. Set to 0 to use Grid Dimension instead.

    - Name: ``voxelSize``
    - Type: ``float``
    - Default Value: ``0.1``
    - Min Value: ``0.0``

Erosion Steps
^^^^^^^^^^^^^

Number of erosion steps. Controls how much the level set can shrink/erode the shape.

    - Name: ``erode``
    - Type: ``float``
    - Default Value: ``8``
    - Min Value: ``0.0``

Closing Threshold
^^^^^^^^^^^^^^^^^

Size of the largest geometric feature or gap beyond which the algorithm should erode no further. Higher values close more holes and gaps in the mesh.

    - Name: ``threshold``
    - Type: ``float``
    - Default Value: ``0``
    - Min Value: ``0.0``

Adaptive Meshing Threshold
^^^^^^^^^^^^^^^^^^^^^^^^^^

Controls adaptive meshing. 0 = no adaptive meshing (uniform tessellation), 1 = most adaptive (fewest triangles).

    - Name: ``adaptivity``
    - Type: ``float``
    - Default Value: ``0``
    - Min Value: ``0.0``
    - Max Value: ``1.0``

