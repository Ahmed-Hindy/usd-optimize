.. AUTO GENERATED FILE - DO NOT EDIT

============
Mesh Cleanup
============

**Key**: ``meshCleanup``

Applies various cleanups to a mesh: merge vertices that are closer to one another than a
given tolerance, remove degenerate faces, make the result manifold, and/or remove isolated vertices. Each
cleanup is an independent toggle, so a config can run just the passes it needs.

How the flags interact
----------------------

The merge sub-flags (``mergeBoundaries``, ``mergeNeighbors``, ``contractDegenerateEdges``) only take
effect when ``mergeVertices`` is enabled; they refine *which* coincident vertices are merged. The
cleanups run in a fixed order (merge, then degenerate/duplicate face removal, then optional manifold and
isolated-vertex passes), so enabling several at once is the normal case.

When to enable coorientFaces and makeManifold
---------------------------------------------

``coorientFaces`` (default ``false``) reverses the winding of a minority of faces to enforce consistent
orientation at shared edges; enable it when a mesh renders with flipped or black faces from inconsistent
winding. ``makeManifold`` (default ``false``) forces a manifold result and is the heaviest pass; enable
it only when a downstream consumer (a renderer, or a boolean/level-set operation) requires manifold
input, since it can alter topology.

Tolerance and units
-------------------

``tolerance`` is the maximum distance, in **stage units**, between two vertices for them to be merged. The
default ``0`` merges only exactly coincident vertices. A non-zero tolerance depends on scene scale, so
scale it with the stage's ``metersPerUnit`` (a value sensible in a centimetre scene is 100x too large in
a metre scene).

Recommended pipelines
---------------------

A common data-quality baseline is ``generateNormals`` -> ``meshCleanup`` -> ``computeExtents``. Run
``meshCleanup`` before ``decimateMeshes`` so decimation operates on clean topology.

Starting configurations
-----------------------

Standard cleanup (defaults):

.. code-block:: json

    [{"operation": "meshCleanup", "mergeVertices": true, "removeDegenerateFaces": true, "removeIsolatedVertices": true}]

Full repair (manifold, consistent winding):

.. code-block:: json

    [{"operation": "meshCleanup", "mergeVertices": true, "removeDegenerateFaces": true, "coorientFaces": true, "makeManifold": true}]


Arguments
---------

Meshes To Process
^^^^^^^^^^^^^^^^^

Optional list of prim paths to consider

    - Name: ``paths``
    - Type: ``[string]``
    - Default Value: ``[]``

Merge Vertices
^^^^^^^^^^^^^^

Merge vertices

    - Name: ``mergeVertices``
    - Type: ``bool``
    - Default Value: ``True``

Tolerance
^^^^^^^^^

The tolerance (distance) apart for vertices to be considered equal

    - Name: ``tolerance``
    - Type: ``float``
    - Default Value: ``0``
    - Min Value: ``0.0``

Merge Boundaries
^^^^^^^^^^^^^^^^

Merge coincident boundary vertices

    - Name: ``mergeBoundaries``
    - Type: ``bool``
    - Default Value: ``True``

Merge Neighbors
^^^^^^^^^^^^^^^

Merge coincident vertices that are neighbors around some face

    - Name: ``mergeNeighbors``
    - Type: ``bool``
    - Default Value: ``True``

Contract degenerate edges
^^^^^^^^^^^^^^^^^^^^^^^^^

Merge consecutively repeated vertex references around faces

    - Name: ``contractDegenerateEdges``
    - Type: ``bool``
    - Default Value: ``True``

Remove degenerate faces
^^^^^^^^^^^^^^^^^^^^^^^

Remove faces with fewer than 3 distinct vertex references

    - Name: ``removeDegenerateFaces``
    - Type: ``bool``
    - Default Value: ``True``

Remove isolated vertices
^^^^^^^^^^^^^^^^^^^^^^^^

Remove isolated vertices

    - Name: ``removeIsolatedVertices``
    - Type: ``bool``
    - Default Value: ``True``

Remove duplicate (lamina) faces
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Remove duplicate (lamina) faces

    - Name: ``removeDuplicateFaces``
    - Type: ``bool``
    - Default Value: ``True``

Coorient Faces
^^^^^^^^^^^^^^

Reverses the winding of a minority of faces to enforce consistent (manifold) orientation at all edges shared by two faces

    - Name: ``coorientFaces``
    - Type: ``bool``
    - Default Value: ``False``

Make Manifold
^^^^^^^^^^^^^

Ensure the final result is a manifold mesh

    - Name: ``makeManifold``
    - Type: ``bool``
    - Default Value: ``False``

