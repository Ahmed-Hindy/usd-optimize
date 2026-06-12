======================
Performance Validators
======================

When evaluating the data in a USD stage, it can be hard to know which
optimizations would actually help. To support this, Usd Optimize ships a set of
**performance validators**: validation rules that use the operations'
:ref:`analysis mode<analysis-mode>` to inspect a stage and flag potential
problems, without modifying it.
Many of the validators also provide suggestions that can be used by
``usd-validation-nvidia`` to automatically fix the discovered issues in the
stage.

The validators integrate with NVIDIA's ``usd-validation-nvidia`` framework.
They live in the ``usd_optimize.validators`` Python package and are registered
as rules under two categories: **Omni:Geometry** and **Usd:Performance**.

.. _analysis-mode:

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

.. Note:: A performance-relevant detail of the implementation: analysis results
   are cached per root layer, so rules in the same family (for example the mesh
   cleanup rules) share a single analysis pass. Mesh-only rules are also
   short-circuited on stages that contain no ``UsdGeomMesh`` prims.

Omni:Geometry
-------------

These rules check for low-level geometric defects on meshes. Most are fixed with
the :doc:`Mesh Cleanup<operations/meshCleanup>` operation.

ColocatedVerticesChecker
    Reports prims with vertices that are collocated and can be merged.

DuplicateFaceChecker
    Reports mesh prims with duplicate (lamina) faces.

IndexedPrimvarChecker
    Reports primvar values that are not referenced by their indices and can be
    removed with :doc:`Optimize Primvars<operations/optimizePrimvars>`. Works on
    non-time-varying geometry.

IsolatedVerticesChecker
    Reports mesh prims that have isolated (unreferenced) vertices.

NonManifoldChecker
    Reports mesh prims with non-manifold geometry. Fixes may also be applied via
    the :doc:`Manifold Meshes<operations/manifoldMeshes>` operation.

ZeroAreaFacesChecker
    Reports prims that contain zero-area faces.

Usd:Performance
---------------

These rules check for stage- and scene-level conditions that affect performance.

CoincidingGeometryChecker
    Finds meshes from different prims whose geometry coincides at the same world
    location. Tagged using :doc:`Find Coincident Geometry<operations/findCoincidingGeometry>`.

DuplicateGeometryChecker
    Finds geometric prims that are exact duplicates; fixed by creating instances
    with :doc:`De-duplicate Geometry<operations/deduplicateGeometry>`.

FuzzyDuplicateGeometryChecker
    Finds geometric prims that match within a tolerance. The vertex positions
    need not match — only the surface shape. Fixed with :doc:`De-duplicate Geometry<operations/deduplicateGeometry>`.

DuplicateMaterialsChecker
    Finds duplicate materials; fixed by deduplicating them with :doc:`Optimize Materials<operations/optimizeMaterials>`.

EmptyLeafChecker
    Reports empty leaf prims such as ``Xform`` or ``Scope``; fixed with
    :doc:`Prune Leaves<operations/pruneLeaves>`.

FindOverlappingMeshesChecker
    Reports meshes that overlap one another in the scene. See :doc:`Find Overlapping Meshes<operations/findOverlappingMeshes>`.

FlatHierarchiesChecker
    Reports prims with a large number of children (a flat hierarchy). See
    :doc:`Find Flat Hierarchies<operations/findFlatHierarchies>`.


HighVertexCountChecker
    Reports meshes with high vertex counts. The reported levels are *High*
    (> 100,000), *Very High* (> 500,000), and *Extreme* (> 1,000,000).

InvisiblePrimsChecker
    Finds invisible prims that can be deactivated.

NormalsChecker
    Reports mesh prims whose normals are aligned to face orientation; fixed with
    :doc:`Generate Normals<operations/generateNormals>`.

OccludedMeshesChecker
    Reports meshes that are occluded; uses :doc:`Find Occluded Meshes<operations/findOccludedMeshes>`.

PrimitiveFitChecker
    Reports meshes that can be replaced with a USD shape prim using :doc:`Fit Primitives<operations/fitPrimitives>`.

RedundantTimeSamplesChecker
    Reports redundant time samples that can be removed with :doc:`Optimize Time Samples<operations/optimizeTimeSamples>`.

RtxMeshCountChecker
    Reports when the RTX mesh count exceeds recommended limits. See :doc:`RTX Mesh Count<operations/rtxMeshCount>`.

SmallMeshChecker
    Reports mesh prims whose extent is below a configurable size threshold; see
    :doc:`Remove Small Geometry<operations/removeSmallGeometry>`.

SparseMeshChecker
    Finds prims that contain multiple disjoint meshes with a low density relative
    to the prim's bounding box. These can be split or clustered with others.

UnusedUVsChecker
    Reports unused texture-coordinate primvars; fixed with :doc:`Remove Unused UVs<operations/removeUnusedUVs>`.

WindingsChecker
    Finds meshes with inconsistent normal winding order; fixed with :doc:`Mesh Cleanup<operations/meshCleanup>`.

ZeroExtentChecker
    Finds degenerate, zero-extent-volume meshes; analyzed and removed with
    :doc:`Remove Small Geometry<operations/removeSmallGeometry>`.
