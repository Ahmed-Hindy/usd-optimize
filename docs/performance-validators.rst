======================
Performance Validators
======================

When evaluating the data in a USD stage, it can be hard to know which
optimizations would actually help. To support this, Usd Optimize ships a set of
**performance validators**: validation rules that use the operations analysis
mode to inspect a stage and flag potential problems, without modifying it.
Many of the validators also provide suggestions that can be used by
``usd-validation-nvidia`` to automatically fix the discovered issues in the
stage.

The validators integrate with NVIDIA's ``usd-validation-nvidia`` framework.
They live in the ``usd_optimize.validators`` Python package and are registered
as rules under two categories: **Omni:Geometry** and **Usd:Performance**.

Registering and running the validators
---------------------------------------

The validators are discovered through ``importlib.metadata`` entry points, so the
``nvidia_usd_validate`` CLI only sees them once the ``usd-optimize`` wheel is
**pip-installed** (a source-tree ``PYTHONPATH`` alone registers no entry-point
metadata). Third-party callers that import the package directly can register all
rules programmatically:

.. code-block:: python

   from usd_optimize.validators import register_all

   register_all()   # registers every Usd Optimize rule with Asset Validator

Once registered, the rules run like any other ``usd-validation-nvidia`` rule, and
report the affected prims along with the operation that would fix them.

.. GENERATED_DOCS_BEGIN - do not edit manually - see tools/repoman/docs_gen.py

Usd:Performance
---------------

These rules check for stage- and scene-level conditions that affect performance.

CoincidingGeometryChecker
^^^^^^^^^^^^^^^^^^^^^^^^^
Finds cases where two or more prims have coinciding geometry that exists within the same world space in the scene. 

DuplicateGeometryChecker
^^^^^^^^^^^^^^^^^^^^^^^^
Find geometric prims that are duplicates; fixed by creating instances. 

FuzzyDuplicateGeometryChecker
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
Finds geometric prims that match within a tolerance. The vertex positions need not match — only the surface shape. 

DuplicateMaterialsChecker
^^^^^^^^^^^^^^^^^^^^^^^^^
Finds duplicate materials; fixed by deduplicating them. 

EmptyLeafChecker
^^^^^^^^^^^^^^^^
Check a stage for redundant leaf primitives (Scopes, Xforms). 

FindOverlappingMeshesChecker
^^^^^^^^^^^^^^^^^^^^^^^^^^^^
Reports meshes that overlap one another in the scene. 

FlatHierarchiesChecker
^^^^^^^^^^^^^^^^^^^^^^
Reports prims with a large number of children (a flat hierarchy). 

HighVertexCountChecker
^^^^^^^^^^^^^^^^^^^^^^
Check a stage for meshes with high or extreme vertex counts. 

InvisiblePrimsChecker
^^^^^^^^^^^^^^^^^^^^^
Finds invisible prims in the stage that can be deactivated instead. 

NormalsChecker
^^^^^^^^^^^^^^
Checks mesh prims for normals aligned to face orientation. 

Returns all prims with normals not aligned with face winding order as a single warning, with an option to fix using scene optimizer operations. 

OccludedMeshesChecker
^^^^^^^^^^^^^^^^^^^^^
Uses Usd Optimize to analyze a scene checking for occluded meshes. 

**Parameters:** 


- `USE_GPU`: Choose whether to use GPU or CPU algorithm. Default: `False`. 
- `CHECK_TRANSPARENCY`: Exclude meshes with opacity < 1.0 from occlusion testing. Default: `True`. 
- `CLUSTERED`: Split the stage into clusters of meshes with overlapping bounding boxes and check visibility per cluster, improving both accuracy and performance by reducing the number of meshes compared at the same time. Default: `True`. 
- `MINIMUM_GAP_SIZE`: The minimum gap size corresponding to the spacing of the background grid. Gaps smaller than this value are considered closed for occlusion culling. The actual grid spacing is max(minimumGapSize, maxDim/maximumGridResolution). Very small values defer to maximumGridResolution for spacing, producing a finer grid that detects smaller gaps and results in fewer meshes being flagged as occluded. It is essentially a tolerance for how sealed an enclosure needs to be: e.g. a value of 3.5 means ignore any opening smaller than 3.5 scene units when deciding if something is hidden. Default: `0.01`. 
- `MAXIMUM_GRID_RESOLUTION`: The maximum number of cells along the longest axis of the grid used for visibility checking. This caps the grid resolution to prevent excessive memory and compute costs (the grid is 3D, so memory scales with the cube of resolution). A value of 500 is suitable for powerful GPUs, use smaller values for less powerful GPUs or CPUs. Default: `500`. 

PrimitiveFitChecker
^^^^^^^^^^^^^^^^^^^
Check mesh prims that could be replaced with a USD primitive prim, with an option to apply the fix from scene optimizer operation. 

RedundantTimeSamplesChecker
^^^^^^^^^^^^^^^^^^^^^^^^^^^
Uses Usd Optimize to analyze a scene checking for redundant time samples. 

RtxMeshCountChecker
^^^^^^^^^^^^^^^^^^^
Check if the number of RTX meshes exceeds recommended limits. 

SmallMeshChecker
^^^^^^^^^^^^^^^^
Uses Usd Optimize to analyze a scene checking for meshes with extents below a configurable size threshold. 

**Parameters:** 


- `SIZE_THRESHOLD`: The minimum extent size a mesh can have before it is considered small. Default: `0.001`. 

SparseMeshChecker
^^^^^^^^^^^^^^^^^
Finds mesh prims that are considered sparse, this can be due to density of the geometry volume in relation to the extent volume, or prims with many sparse disjoint meshes. 

These prims will be either identified as needing to be diced, split, or clustered together with other similar sparse meshes within the scene. 

UnusedUVsChecker
^^^^^^^^^^^^^^^^
Check a stage for unused texture coordinate primvars. 

WindingsChecker
^^^^^^^^^^^^^^^
Finds and fixes meshes with inconsistent windings. 

ZeroExtentChecker
^^^^^^^^^^^^^^^^^
Uses Usd Optimize to analyze a scene checking for geometry that has zero sized extents. 

Omni:Geometry
-------------

These rules check for low-level geometric defects on meshes. Most are fixed with the :doc:`Mesh Cleanup<operations/meshCleanup>` operation.

ColocatedVerticesChecker
^^^^^^^^^^^^^^^^^^^^^^^^
Check mesh prims for colocated vertices, returns all prims with colocated vertices as a single warning with an option to fix via scene optimizer operation. 

DuplicateFaceChecker
^^^^^^^^^^^^^^^^^^^^
Check mesh prims for duplicate faces, returns all prims as a single warning with an option to fix via scene optimizer operation. 

IndexedPrimvarChecker
^^^^^^^^^^^^^^^^^^^^^
For Primvars with non-constant values of interpolation, it is often the case that the same value is repeated many times in the array. 

An indexed primvar can be used in such cases to optimize for data storage if the primvar's interpolation is non-constant (i.e. uniform, varying, face varying or vertex). 

This Checker also looks for indexed primvars whose indices are out of bounds, or use a non-constant interpolation but do not contain array-type data. 

IsolatedVerticesChecker
^^^^^^^^^^^^^^^^^^^^^^^
Check mesh prims for isolated vertices, returns all prims as a single warning with an option to fix via scene optimizer operation. 

NonManifoldChecker
^^^^^^^^^^^^^^^^^^
Check mesh prims for non-manifold geometry, returns all non-manifold prims as a single warning with an option to fix via scene optimizer operation. 

ZeroAreaFacesChecker
^^^^^^^^^^^^^^^^^^^^
Check mesh prims for any zero area faces, returns all prims that have zero area faces as single warning with an option to fix using the scene optimizer operation. 

.. GENERATED_DOCS_END
