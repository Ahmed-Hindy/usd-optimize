// SPDX-FileCopyrightText: Copyright (c) 2020-2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
// SPDX-License-Identifier: Apache-2.0
//

#pragma once

// Usd Optimize Core
#include "usd_optimize/core/Defs.h"
#include "usd_optimize/core/UsdIncludes.h"


namespace usd_optimize
{

// Compute and set the extent attribute on the specified meshes.
///
/// Returns the number of prims that have had their extents computed by this function.
USD_OPTIMIZE_EXPORT
size_t _computeExtents(const std::vector<PXR_NS::UsdPrim>& prims);

// Compute and set the extent attribute on the specified meshes.
///
/// Returns the number of prims that have had their extents computed by this function.
USD_OPTIMIZE_EXPORT
size_t _computeExtents(const PXR_NS::UsdStageWeakPtr& usdStage, const std::vector<std::string>& meshPrimPaths);

/// Find boundable prims that are missing an authored ``extent`` attribute.
///
/// Applies the same prim filter as :func:`_computeExtents` (``UsdGeomMesh`` /
/// ``UsdGeomPoints``, skipping instance proxies). Returns the prim paths of
/// prims for which extents are not currently authored — i.e. the set of
/// prims that an unconstrained ``computeExtents`` invocation would author
/// onto. Used by the analysis-mode entry point to surface findings without
/// mutating the stage.
USD_OPTIMIZE_EXPORT
std::vector<std::string> _findPrimsMissingExtents(const std::vector<PXR_NS::UsdPrim>& prims);

USD_OPTIMIZE_EXPORT
std::vector<std::string> _findPrimsMissingExtents(const PXR_NS::UsdStageWeakPtr& usdStage,
                                                  const std::vector<std::string>& meshPrimPaths);

} // namespace usd_optimize
