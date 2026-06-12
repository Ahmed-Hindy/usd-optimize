.. AUTO GENERATED FILE - DO NOT EDIT

=======================
Deduplicate Hierarchies
=======================

**Key**: ``deduplicateHierarchies``

Find duplicate prim hierarchies and replace duplicates with instanceable internal references to a prototype. Identical hierarchies that contain variants will produce one prototype per variant. Recurses into each prototype so nested duplicates are consolidated into nested instanceable references.

Arguments
---------

Prim Paths
^^^^^^^^^^

Optional subtree roots. Empty = walk children of the default prim.

    - Name: ``paths``
    - Type: ``[string]``
    - Default Value: ``[]``

Tolerance
^^^^^^^^^

Acceptable difference for floating-point properties when comparing subtrees: scalar float/double/half, vectors, matrices (including descendant xformOp:transform), quaternions, and arrays of any of these (points, normals, UVs, etc.). The value is in stage units. Integer/topology indices, strings, tokens and bools always require an exact match regardless of tolerance. Set to 0 for bitwise-exact comparison.

    - Name: ``tolerance``
    - Type: ``float``
    - Default Value: ``0.001``

Ignore Shader Outputs
^^^^^^^^^^^^^^^^^^^^^

Skip shader output attributes (outputs:surface, outputs:displacement, etc.) during value comparison. These often differ between material instances even when the geometry is identical. Enabled by default.

    - Name: ``ignoreShaderOutputs``
    - Type: ``bool``
    - Default Value: ``True``

Max Depth
^^^^^^^^^

Maximum number of breadth-first levels to descend, counting from the children of the default prim (or of `paths`) as level 1. 0 (the default) means unbounded. Because the operation recurses into each prototype to build a nested-instance library, deep hierarchies can reach many levels; cap this to bound runtime or to avoid consolidating very deeply nested instances.

    - Name: ``maxDepth``
    - Type: ``int``
    - Default Value: ``0``

