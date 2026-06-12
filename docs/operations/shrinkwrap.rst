.. AUTO GENERATED FILE - DO NOT EDIT

==========
Shrinkwrap
==========

**Key**: ``shrinkwrap``

This operation converts meshes to a level set volume using `OpenVDB <https://www.openvdb.org/>`_ and extracts a watertight mesh back out.
It is useful for closing holes, simplifying topology, and creating LOD meshes.

The algorithm works by rasterizing the input mesh into a narrow-band level set, optionally eroding the surface to close gaps and holes, and then extracting a new polygon mesh from the resulting volume.
Resolution is controlled by either a voxel size or a grid dimension limit.
The output mesh is written as a new sibling prim alongside the original, which is preserved.

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

