==============================
Which Operations Should I Use?
==============================

Usd Optimize provides a range of operations that can be applied to a stage.
These can be used as a single operation or combined together into a processing
stack (a JSON array of operations applied in order). Determining which
operations and options to pick is not always easy: it depends on the specific
contents of the scene and the type of optimization that will improve your target
workflow. This guide offers some guidelines for how to approach optimization and
why these choices might help.

.. Tip:: Before optimizing blindly, run the :doc:`performance-validators` over
   your stage. The validators analyze the scene and report which operations
   would actually benefit it, so you can target your stack instead of guessing.
   Many of the validators also provide suggestions that can be used by
   ``usd-validation-nvidia`` to automatically fix the discovered issues in the
   stage.

Consider What To Solve
----------------------

The first step is to decide what problem you are trying to solve. Large, complex
scenes commonly suffer from one or more of:

- The scene uses too much memory, either system memory or video memory.
- The scene is too slow to interact with, either tumbling the camera or playing
  back animation.
- The scene is slow to load.

Improving Memory Usage
----------------------

If the scene uses too much memory, look for optimizations that reduce the
resources needed by the scene.

De-duplicate Geometry
#####################

This replaces multiple copies of identical meshes with a single instance
prototype plus references to it. Because a reference uses less memory than a full
mesh, this can reduce both system memory and GPU memory.

.. Note:: This is only effective if there are meshes that are identical but not
   already instanced; it may have no effect on your scene. Run
   :doc:`De-duplicate Geometry<operations/deduplicateGeometry>` in analysis mode (or the
   ``DuplicateGeometryChecker`` validator) first to see whether duplicates exist.

Optimize Materials
##################

If a scene has a large number of materials, some may be duplicates. Run
:doc:`Optimize Materials<operations/optimizeMaterials>` to replace duplicate materials with
references to a single unique material, reducing memory usage and improving
performance.

- **Convert To Color** replaces materials with a per-vertex ``displayColor``
  primvar. If there are many materials in the scene this significantly reduces
  prim count, speeding up loading and interactivity. Resolving MDLs can be slow,
  so using colors instead can greatly reduce load times — although there will be
  no material shading, only colors.

Improving Interactive Performance
---------------------------------

If the scene has poor interactive performance (low FPS), look for optimizations
that reduce the number of prims or mesh complexity. A large number of prims can
affect performance significantly.

Merge Static Meshes
###################

:doc:`Merge<operations/merge>` replaces multiple meshes that share common
properties with a single merged mesh. This reduces prim count and can improve
interactive performance. Because the total amount of geometry does not change,
it will not reduce memory consumption. Meshes can also be clustered and merged
spatially, which can improve render performance by creating tighter bounding
volumes.

.. Caution:: Once meshes are merged you can no longer edit the individual
   originals, only the new merged mesh prims. Merged meshes can be separated
   again using :doc:`Split Meshes<operations/splitMeshes>`.

Decimate Meshes
###############

Reducing mesh complexity and face count is an effective way to improve
interactive performance and reduce memory usage. :doc:`Decimate Meshes<operations/decimateMeshes>`
can reduce meshes by an overall percentage or to a defined error tolerance, and
can be guided by normals to retain original mesh features.

Find Occluded Meshes
####################

If there are meshes in the stage that are not visible to any camera (because
they are enclosed by other geometry), :doc:`Find Occluded Meshes<operations/findOccludedMeshes>`
can identify them so they can be deactivated or hidden, improving load times and FPS.

Optimize Skeleton Roots
#######################

A good option if you have rigged characters that use ``UsdSkel``.
:doc:`Optimize Skeleton Roots<operations/optimizeSkelRoots>` merges all meshes on a skeleton
into a single mesh, which can greatly improve character playback speed by
optimizing for GPU skinning. As with merging static meshes, this will not
significantly reduce memory usage.

.. Note:: Reducing the memory a stage consumes can also speed up load and
   evaluation, since less data needs to be read and processed.

Other Tools
-----------

These operations do not directly affect performance but may improve usability
and downstream workflows:

Compute Pivot
#############

:doc:`Compute Pivot<operations/pivot>` places the parent transform at the center
of an object's bounding box, making it easier to interact with the object
because the transform manipulator is centered on it. Some tools generate scenes
where the transform sits at the origin, far from the actual vertices, making
precise manipulation difficult.

Compute Extents
###############

Extents are the axis-aligned bounding boxes of meshes; they do not always exist
in a USD file. :doc:`Compute Extents<operations/computeExtents>` authors them, which can
improve performance because the application then knows the exact bounds of an
object without computing them.

Advanced Functionality
-----------------------

Python Script
#############

:doc:`Python Script<operations/pythonScript>` executes user-defined Python code with
access to the USD stage. Use it to add custom logic, build optimization stacks
specific to your needs, and make them reusable via JSON config files.

Split Meshes
############

:doc:`Split Meshes<operations/splitMeshes>` is helpful for debugging and finding spatial
outliers. Using ``Spatial Clustering Mode``, meshes are split and merged
spatially in a single pass, which improves processing performance versus running
split and merge separately and can improve render performance by creating
smaller bounding volumes.

Mesh Cleanup
############

Poorly constructed geometry can affect how renderers interpret a mesh and slow
down rendering. :doc:`Mesh Cleanup<operations/meshCleanup>` can merge vertices and make
meshes manifold, which can improve render performance.

.. Note:: The :doc:`performance-validators` can identify many of these
   incompatible-mesh conditions automatically.

Remesh Meshes
#############

If a problematic mesh exists in the stage, :doc:`Remesh Meshes<operations/remeshMeshes>`
generates new topology for it. This is helpful when a mesh is not rendering or
performing as intended from its original source tool. Combined with decimation,
it is an effective way to clean and optimize geometry.

Summary of Expected Performance Improvements
--------------------------------------------

.. table::
   :widths: 20 20 15 15 15 15

   ============ ============== =========== =========== =========== =======
   Process      Options        Load Time   CPU RAM     GPU RAM     FPS
   ============ ============== =========== =========== =========== =======
   Merge        By Selection   Slight      No          No          Yes
   Merge        By Material    Slight      No          No          Yes
   Merge        Rigid Body     Slight      No          No          Yes
   Merge        By Skeleton    Slight      No          No          Yes
   Merge        By Spatial     Yes         No          No          Yes
   Decimate     Tol./Reduction Yes         Yes         Yes         Yes
   Deduplicate  Instances      Yes         Yes         No          Slight
   Opt Mats     Deduplicate    Yes         Yes         Yes         Yes
   Opt Mats     Convert Color  Yes         Yes         Yes         Yes
   ============ ============== =========== =========== =========== =======

Inspecting The Results
----------------------

Each operation returns a result (and, in many cases, a structured output
dictionary) describing what it changed. When driving a stack through Python or
the JSON helpers, inspect the returned ``(success, error, output)`` tuples to see
what each operation did.

To measure the real-world effect of an optimization, compare the relevant
metrics for the stage before and after running your stack:

- If **reducing memory** was the goal, compare system and GPU memory of the
  loaded scene in your target application.
- If **improving performance** was the goal, compare the FPS and/or playback
  speed of the original and optimized scenes.

If a particular optimization is not beneficial, try a different one on the
original scene.

Try Fixing in the Source Data Application
#########################################

Usd Optimize may surface problems that are better solved upstream. For example,
if :doc:`De-duplicate Geometry<operations/deduplicateGeometry>` is able to replace a lot of
geometry with instances, the asset may have been authored without instancing in
the first place. Where possible, replacing geometry with instances in the source
tool has the additional benefit of improving the source data itself.

Use Caution
-----------

Some optimizations can affect performance in both positive and negative ways. For
example, merging meshes that were originally instances will *increase* memory
usage, because each instance must be converted into a new geometry prim. Decide
up front what trade-offs are acceptable for the consumer of the data. If
increased memory usage is acceptable to achieve a higher frame rate, then such an
operation is still worthwhile.
