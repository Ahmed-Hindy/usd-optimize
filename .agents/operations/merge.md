<!-- SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved. -->
<!-- SPDX-License-Identifier: Apache-2.0 -->

# Merge Static Meshes

**Key:** `merge`
**Source:** `source/operations/merge/Merge.cpp`

## Overview

Merge Static Meshes combines multiple meshes that share common properties into single merged meshes. This reduces scene prim count and draw calls, improving overall rendering performance.

Meshes are grouped ("bucketed") based on shared properties — material bindings, vertex attributes, etc. Within each bucket, meshes are combined into a single mesh. **`considerMaterials`** ensures meshes with different materials stay separate (or are merged with geometry subsets). Spatial clustering options can further subdivide merges to maintain reasonable mesh sizes.

The merge operation uses a clustering module that supports multiple spatial modes: no spatial grouping, bounding-box-based grouping, vertex-count-based grouping, and coincident-boundary grouping.

The **`CoincidentBoundary`** mode (`spatialMode: 3`) only merges meshes that share a "seam" — at least `boundaryMinSharedVertices` (default 2) *boundary vertices* that coincide in world space (within `boundaryTolerance`). A boundary vertex is a vertex lying on a boundary edge (an edge used by exactly one face). Connectivity is transitive, so a chain of abutting meshes collapses into one. Meshes that share no seam are left untouched. This targets bad CAD output where a single part is exported as several abutting pieces (e.g. a washer split into two half-rings).

Requiring two or more shared vertices (rather than one) avoids merging parts that merely touch at a single corner point, while still catching seams whose tessellation differs on each side — there the boundary *vertices* coincide even though the boundary *edges* don't line up. If two pieces that clearly share a seam aren't merging, they likely share fewer than `boundaryMinSharedVertices` coincident vertices (mismatched tessellation that only touches at points); lower the threshold to `1` to merge on any single shared vertex.

## Parameters

| Parameter | Type | Default | Description |
|---|---|---|---|
| `meshPrimPaths` | string[] | `[]` (all meshes) | Prim paths to consider for merging. Empty = all meshes. |
| `considerMaterials` | bool | `false` | Keep differently-materialed meshes separate. |
| `materialAlbedoAsVertexColors` | bool | `false` | Convert material albedo to vertex colors during merge. |
| `originalGeomOption` | enum | `Delete` (1) | What to do with original geometry: `Ignore` (0), `Delete` (1), `Deactivate` (2), `Hide` (3). |
| `mergePoint` | enum | `Default` (0) | Where to create merged prims: `Default` (0), `Root` (1), `Parent` (2). |
| `rootPath` | string | `""` | Root path for merged output prims. |
| `considerAllAttributes` | bool | `false` | Consider all vertex attributes for bucketing. |
| `allowSingleMeshes` | bool | `false` | Allow buckets with a single mesh. |
| `spatialMode` | enum | `None` (0) | Spatial clustering: `None` (0), `BoundingBox` (1), `VertexCount` (2), `CoincidentBoundary` (3). |
| `spatialThreshold` | float | `10.0` | Spatial clustering distance threshold (BoundingBox mode). |
| `spatialMaxSize` | float | `0.0` | Maximum spatial cluster size (BoundingBox mode). |
| `spatialVertexCount` | int | `10000` | Target vertex count per cluster (VertexCount mode). |
| `boundaryTolerance` | float | `1e-5` | World-unit distance at which boundary vertices are treated as coincident (CoincidentBoundary mode). |
| `boundaryMinSharedVertices` | int | `2` | Minimum number of coincident boundary vertices two meshes must share to be merged (CoincidentBoundary mode). `1` merges on any single shared corner. |
| `treatAsPrimvars` | string[] | `[]` | Attributes to treat as primvars during merge. |
| `spatialDebug` | bool | `false` | Enable spatial clustering debug output. |

## Tuning Order

1. **`considerMaterials` first** — Keep true to preserve material assignments. Set false to merge everything.
2. **`spatialMode` second** — Enable spatial clustering for large scenes to keep merged meshes at reasonable sizes.
3. **`spatialThreshold` / `spatialMaxSize` third** — Tune clustering parameters.
4. **`originalGeomOption` fourth** — Choose what to do with source meshes after merge.

## Visual Diagnosis

| Symptom | Parameter | Direction | Notes |
|---|---|---|---|
| Want one merged prim per material instead of `GeomSubset`s | `considerMaterials` | Set to `true` | "Keep Materials Separate" — when on, the bucketer hashes by material binding so each material yields its own merged prim. When off (default), differing materials are merged under a single prim with `GeomSubset`s per material; per-material bindings are preserved either way. |
| Merged meshes are too large / cause GPU memory pressure | `spatialMode`, `spatialMaxSize` | Enable / Decrease | Spatial clustering caps cluster size; lowering `spatialMaxSize` produces more, smaller merged meshes. |
| Want to reunite only CAD pieces that share a seam (e.g. a split washer) | `spatialMode`, `boundaryTolerance` | Set to `3` / Tune | `CoincidentBoundary` merges only meshes that share coincident boundary vertices. Raise `boundaryTolerance` if seam vertices don't quite line up; lower it if distinct nearby parts merge incorrectly. |
| Two pieces clearly share a seam but don't merge | `boundaryMinSharedVertices` | Lower to `1` | They likely touch at coincident points but with mismatched tessellation (no shared edge / too few shared vertices). `1` merges on any single shared boundary vertex, at the risk of also merging incidental corner touches. |
| Originals still visible after merge | `originalGeomOption` | Set to `Delete` (1) or `Hide` (3) | Default is `Delete`; choose `Hide` if you need to keep authored prims for downstream workflows. |
| Vertex attributes lost on merge | `considerAllAttributes`, `treatAsPrimvars` | Enable / Add the attribute | Bucketing only matches on the attributes it knows about — opt in for non-standard primvars. |

## Starting Configs

**Standard merge**:
```json
[{"operation": "merge"}]
```

**Merge with spatial clustering**:
```json
[{"operation": "merge", "spatialMode": 1, "spatialThreshold": 100.0, "spatialMaxSize": 500.0}]
```

**Merge only meshes that share a seam (split-CAD repair)**:
```json
[{"operation": "merge", "spatialMode": 3, "boundaryTolerance": 1e-5}]
```

## Prerequisites & Workflows

- Works standalone on any mesh scene.
- Most effective on scenes with many small meshes sharing the same material.
- Common pipeline: `merge` → `shrinkwrap` or `merge` → `generateNormals`.

## Known Limitations

- Merged meshes lose individual prim identity.
- Material bindings are preserved via geometry subsets when `considerMaterials=true`.
- Spatial clustering thresholds are in world units.