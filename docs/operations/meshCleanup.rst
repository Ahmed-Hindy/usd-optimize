.. AUTO GENERATED FILE - DO NOT EDIT

============
Mesh Cleanup
============

**Key**: ``meshCleanup``

Applies various cleanups to a mesh, e.g merge vertices that are closer to one another than a given tolerance, removing degenerate faces, making the resulting mesh be manifold and/or removing any isolated vertices.

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

