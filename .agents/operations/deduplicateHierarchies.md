<!-- SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved. -->
<!-- SPDX-License-Identifier: Apache-2.0 -->

# Deduplicate Hierarchies

**Key:** `deduplicateHierarchies`
**Source:** `source/operations/deduplicateHierarchies/DeduplicateHierarchies.cpp`

> **Safety note.** Duplicates are identified by subtree shape — the
> operation only merges prims whose hierarchy structure, prim types, and
> authored property names are identical, then refines the candidate
> groups by comparing all authored property values. This is safe on any
> asset.
>
> For per-mesh duplicate detection based on actual geometry, use
> `deduplicateGeometry` instead — typically as a follow-up step.

## Overview

Deduplicate Hierarchies finds duplicate prim *hierarchies* (whole subtrees) and replaces duplicates with instanceable internal references to the first instance (the prototype). The prototype keeps its authored content; every other duplicate gets its children deleted, an internal reference authored to the prototype, and `instanceable=true` set on it. Because the prototype is then traversed in turn, duplicates nested *inside* a prototype are themselves consolidated into **nested instanceable references**, so repeated sub-assemblies are deduplicated at every depth — all with internal references in the same stage.

Unlike `deduplicateGeometry`, which compares individual meshes by vertex data, this operation compares *hierarchies*. Prims are grouped by an FNV-1a hash of each subtree's shape, prim type names, and sorted authored property names, then a full property-value comparison verifies that all authored property **values** match (excluding xformOp values on the root prim, which represent placement; descendant transforms must match within `tolerance`). This is safe on any asset — structurally identical subtrees with different mesh data, material parameters, etc. will NOT be collapsed.

It walks **breadth-first** under the default prim (or under the user-supplied `paths` if non-empty) and, at each level, groups prims by structural hash. Each structural group is then **partitioned into value-equivalence classes** (members whose authored property values match a class representative), and every class with two or more members becomes a duplicate group with its own prototype. A structural group that contains several value-variants therefore yields *one prototype per variant* — not a single first-member comparison. This fixes the common outlier-first case: a value-distinct member that sorts first no longer prevents the remaining matching members from merging.

Once a level produces merges, only the **merged duplicates** are pruned from further traversal — each duplicate's children are deleted and replaced by the reference to the prototype, so there is nothing left to find under it. Every other prim still contributes its children to the next level: prims that grouped structurally but did *not* merge (their values differed, or they were a lone value-variant), prims excluded because they already author references or payloads, and **the prototype of each merged class**. Descending into the prototype lets the operation consolidate duplicates *inside* it into nested instanceable references — every instance that references the prototype inherits that nested structure, so shared inner content is deduplicated once and a deep instance library is built branch by branch. This also covers the unmerged-parent case: a tray that fails to merge at its own level still lets the BFS descend into it to find identical sub-modules inside. Material-related prims (Material/Shader/NodeGraph types, `Looks`/`Materials` scopes, and prims whose name starts with a texture prefix like `Diffuse` or `Normal`) are skipped at every level. Prims that already author references or payloads are excluded from the duplicate set so we don't replace an already-customised instance with a generic reference; they are not pruned, so traversal still descends into their children.

The operation creates internal instanceable references from duplicate subtrees to the first instance (the prototype).

## Parameters

| Parameter | Type | Default | Description |
|---|---|---|---|
| `paths` | string[] | `[]` (whole stage) | Optional subtree roots. When non-empty, the BFS starts at the *children* of each listed prim path. Empty = walk children of the default prim. |
| `tolerance` | float | `0.001` | Acceptable difference for floating-point properties when comparing subtrees: scalar float/double/half, vectors, matrices (including descendant `xformOp:transform`), quaternions, and arrays of any of these (points, normals, UVs, etc.). The value is in stage units. Integer/topology indices, strings, tokens and bools always require exact match regardless of tolerance. Set to 0 for bitwise-exact comparison. Matches `deduplicateGeometry`'s default. |
| `ignoreShaderOutputs` | bool | `true` | Skip shader output attributes (`outputs:surface`, `outputs:displacement`, etc.) during value comparison. These often differ between material instances even when the geometry is identical, so ignoring them lets structurally-identical hierarchies under different material networks still match. Set to `false` for a stricter compare. |
| `maxDepth` | int | `0` (unbounded) | Maximum number of breadth-first levels to descend, counting the children of the default prim (or of `paths`) as level 1. `0` = unbounded. Because the operation recurses into each prototype to build a nested-instance library, deep hierarchies can reach many levels; cap this to bound runtime or to avoid consolidating very deeply nested instances. |

> **Verbose logging.** `verbose` is not an op argument — it's a field on
> `ExecutionContext` (default off). To enable per-level / per-group
> progress logging for this op, prepend an `executionContext` entry to
> the chain: `{"operation": "executionContext", "verbose": true}`.

## Matching behavior

The structural hash covers, per descendant prim: relative path within the subtree, type name, and sorted authored property name tokens. After structural grouping, a **full property-value comparison** partitions each group into value-equivalence classes — within a class, each member matches that class's representative (excluding `xformOp:*` and `xformOpOrder` on the root prim, which represent placement; descendant transforms must match within `tolerance`). Each class with ≥2 members merges to its own prototype. This means different mesh points, UVs, material parameters, internal transforms, or any other authored data split members into separate variants; members that share values still merge among themselves.

Pitfall: a single extra child prim or extra authored attribute changes the *structural* hash and prevents matching entirely. A differing attribute *value* (mesh points, UVs, material parameters) only splits members into separate value-variants — copies that share values still merge — unless `tolerance` is set to absorb the difference. With `tolerance=0.001` (default), small floating-point drift is absorbed so near-identical copies can land in the same variant. Because tolerance-based closeness is not transitive, borderline chains of values may still depend on which member becomes the class representative. Set to 0 for bitwise-exact comparison, or increase for assets with larger numerical drift from re-export or tessellation.

> **Multi-variant groups.** When a set of structurally-identical copies contains a clear minority outlier (e.g. 17 identical + 1 different), the 17 still merge into one prototype and the outlier is left distinct even if the outlier sorts first. Earlier behaviour compared every member to whichever copy sorted first and dropped the rest, so an outlier sorting first could zero out all merges; that is fixed. With nonzero `tolerance`, classes are still representative-based, so ambiguous borderline values can remain order-sensitive.

> **Precision-critical assets.** Because descendant transforms — including `xformOp:transform` — are compared within `tolerance`, subtrees whose only differences are sub-tolerance internal-layout drift will merge. For metrology, simulation, or articulated assets, where small descendant offsets are meaningful rather than re-export noise, set `tolerance=0` to require a bitwise-exact match and avoid absorbing those differences.

> **Performance.** Within each structural group, members are first pre-bucketed by a tolerance-independent value fingerprint (the exact-typed content — integer/topology arrays, strings, tokens, bools — plus float-array *lengths*), and the full pairwise subtree comparison runs only within a bucket. This keeps partitioning near-linear on large, mostly value-distinct groups (parametric CAD) instead of degrading to O(N²) full-subtree walks. The fingerprint is a necessary condition for value-equality, so bucketing never separates a true match; at `tolerance=0` it collapses to a single value hash per subtree (no pairwise compare at all).

When you're unsure, run in analysis mode first and inspect the `{prototype: [duplicates]}` map before committing.

## Tuning Order

1. **`tolerance` first** — Default 0.001. If the operation finds fewer duplicates than expected, try increasing tolerance to absorb floating-point drift from re-export or tessellation. Set to 0 for bitwise-exact comparison. Affects all floating-point types — scalars, vectors, matrices (incl. descendant `xformOp:transform`), quaternions, and arrays of them; integer topology, strings and tokens always require exact match.
2. **`paths` second** — Start with the default (whole-stage scan). Set this only when you need to restrict to a known subtree, or when the default-prim traversal pulls in unrelated content (e.g., a top-level `/Environment` xform).
3. **`ignoreShaderOutputs`** — Default `true`. Flip to `false` only when the user explicitly wants shader output attributes to participate in the value comparison (rare — these usually differ between material instances even when the geometry is identical).
4. **`maxDepth` last** — Default `0` (unbounded). Leave unbounded for maximum reuse. Set a positive cap only to bound runtime on very deep hierarchies, or when very deeply nested instances are undesirable for the downstream consumer.

## Visual Diagnosis

_Not applicable — purely structural. Effects are composition-arc changes (new internal references) and `instanceable=true` flags. Verify by inspecting the stage hierarchy: prototype keeps its authored children, duplicates show up as instanceable refs to the prototype._

## Starting Configs

**Hierarchy-only (single-step)**:
```json
[{"operation": "deduplicateHierarchies"}]
```

**Recommended pipeline** — hierarchy dedup followed by per-mesh dedup. Catches both whole-subtree duplicates and identical meshes that share geometry but sit under different parents. This is the configuration that matches a fully-deduplicated reference asset most closely:
```json
[
  {"operation": "deduplicateHierarchies"},
  {"operation": "deduplicateGeometry", "duplicateMethod": 2, "tolerance": 0.001}
]
```

**With tolerance** for assets that have minor floating-point drift between duplicates (e.g. CAD re-exports):
```json
[{"operation": "deduplicateHierarchies", "tolerance": 0.001}]
```

**Restrict to a known subtree**:
```json
[{"operation": "deduplicateHierarchies", "paths": ["/World/Vegetation"]}]
```

## Prerequisites & Workflows

- **Stage must have a default prim** when `paths` is empty (the default scan starts at the default prim's children).
- **Recommended two-step pipeline**: this operation first (catches whole-subtree duplicates), then `deduplicateGeometry` (catches per-mesh duplicates the hierarchy pass missed because the meshes sit under different parents). Single-step hierarchy dedup typically catches ~70% of what the combined pipeline catches; the rest is per-mesh.
- For per-prototype merging (single mesh per prototype hierarchy) or external payload export to standalone files, those workflows require Kit-side helpers (`omni.kit.commands`, `omni.usd`) and are not available in this standalone library.
- **Save the result via the root layer**, not via `stage.Export()`. `stage.Export()` flattens the composed stage and renames Usd-instance prototypes to synthetic root-level paths (e.g. `/Flattened_Prototype_N`) — functionally equivalent, but loses the authored prototype names. Prefer `stage.GetRootLayer().Export(path)` or an equivalent layer-preserving save. The skill's Tier 1 example shows the correct call.

## Known Limitations

- **Internal references only.** The C++ port covers Mode 1 of the Python processor. Mode 1b (merge prototype meshes) and Mode 2 (external payloads) require Kit-side composition helpers and remain in the Python processor.
- **Material-related skip predicate.** Prims whose name is `Looks` or `Materials`, prims of type `Material`/`Shader`/`NodeGraph`/`GeomSubset`, and prims whose name starts with a texture prefix (`Diffuse`, `Specular`, `Normal`, `Roughness`, `Metallic`, `Emissive`, `Opacity`, `AO`, `Displacement`) are unconditionally skipped. If a hierarchy you expected to dedup is being passed over, it likely matches one of those predicates.
- **Static (default-time) value comparison only.** Property values are compared at their default value. An attribute that authors *only* time samples (no default) reads back no default value, so it is treated as value-less for comparison — two subtrees that differ only in time-sampled data can therefore still merge. This operation targets static hierarchy deduplication; animated overrides are out of scope.
- **Existing references / payloads excluded.** Prims with authored refs or payloads are excluded from duplicate groups, so they aren't overwritten. They are not pruned merely because they were structurally grouped; if they do not actually merge, traversal can still descend into their children and find nested duplicates.
- **No cross-stage support.** The operation only authors references to prims within the same stage. For external payload export, see the Python processor.
- **Transformations on duplicates are preserved.** Setting `instanceable=true` plus authoring an internal reference keeps the duplicate prim's local transform. Visual appearance should match before/after for typical transform-only duplicates; if your duplicates differ in attribute opinions other than transform, those opinions are *removed* (children get deleted before the reference is authored).
