<!-- SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved. -->
<!-- SPDX-License-Identifier: Apache-2.0 -->

# Prune Leaves

**Key:** `pruneLeaves`
**Source:** `source/operations/pruneLeaves/PruneLeaves.cpp`

## Overview

Prune Leaves finds and removes leaf grouping primitives — Xforms and Scopes that contain no meaningful children (or only other empty groups). These empty containers add to prim count without contributing to the scene.

The operation recursively identifies grouping prims (Xform, Scope) whose entire subtree consists only of other empty grouping prims. References are handled specially: if a reference contains only empty groups, the reference itself is considered a leaf.

**`pruneMode`** controls how leaves are handled: delete, deactivate, or hide. **`filterInactive`** excludes inactive prims from the "empty" check — when enabled, an Xform with only inactive children is still considered a leaf.

## Parameters

| Parameter | Type | Default | Description |
|---|---|---|---|
| `paths` | string[] | `[]` (all prims) | Prim paths to search from. Empty = entire stage. |
| `pruneMode` | enum | `Delete` (1) | How to handle leaves: `Delete` (1), `Deactivate` (2), `Hide` (3). `0` is `Ignore`, which would remove nothing — it errors outside analysis mode (in analysis mode the method is moot, since leaves are only reported). |
| `filterInactive` | bool | `false` | Don't count inactive prims as children (treat groups with only inactive children as empty). |
| `preserveUnloadedPayloads` | bool | `true` | Don't prune leaf prims carrying an unloaded payload (they may contribute content once loaded). Set `false` to prune them anyway. |

## Tuning Order

1. **`pruneMode` first** — Use `Delete` for thorough cleanup. Use `Deactivate` for reversible.
2. **`filterInactive` second** — Enable to be more aggressive about pruning groups with deactivated children.

## Visual Diagnosis

_Not applicable — only empty grouping prims are removed; there is no rendered output to diagnose. If meaningful prims disappear, check that they aren't typed as `Xform`/`Scope` with all-empty subtrees._

## Starting Configs

**Standard pruning** (delete):
```json
[{"operation": "pruneLeaves", "pruneMode": 1}]
```

**Conservative pruning** (deactivate, reversible):
```json
[{"operation": "pruneLeaves", "pruneMode": 2}]
```

## Prerequisites & Workflows

- Works standalone on any USD stage.
- Supports analysis mode for usd-validation-nvidia integration.
- Common pipeline: `removePrims` → `pruneLeaves` (remove empty groups left after prim removal).

## Known Limitations

- Only considers Xform and Scope typed prims as grouping prims.
- Instance proxies are filtered out before pruning.
- References are handled as atomic units — if a reference subtree is all leaves, the reference root is pruned.
- A grouping prim carrying an **unloaded payload** is preserved by default (`preserveUnloadedPayloads`). With its payload unloaded it composes no children and looks empty, but it may contribute meaningful content once loaded, so it (and any ancestor whose only descendants are such prims) is kept. Set `preserveUnloadedPayloads=false` to prune them anyway.