// SPDX-FileCopyrightText: Copyright (c) 2020-2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
// SPDX-License-Identifier: Apache-2.0
//

#pragma once

// Usd Optimize Core
#include "usd_optimize/core/Defs.h"
#include "usd_optimize/core/UsdIncludes.h"

// Mesh Tools
#include <MeshTools/ClashDetector.h>
#include <MeshTools/Stage.h>

// C++
#include <memory>


namespace usd_optimize
{

USD_OPTIMIZE_EXPORT
std::shared_ptr<MeshTools::Stage> GetStage(const PXR_NS::UsdStageRefPtr& usdStage,
                                           const std::vector<PXR_NS::UsdPrim>& prims,
                                           bool checkTransparency = false);

USD_OPTIMIZE_EXPORT
PXR_NS::GfMatrix4d _getTransformFromToFuzzy(const PXR_NS::VtVec3fArray& sourcePoints,
                                            const PXR_NS::VtIntArray& sourceIndices,
                                            const PXR_NS::VtIntArray& sourceFaceSizes,
                                            const PXR_NS::VtVec3fArray& targetPoints,
                                            const PXR_NS::VtIntArray& targetIndices,
                                            const PXR_NS::VtIntArray& targetFaceSizes);

/// Computes the fuzzy (OBB-based) transform from one fixed source mesh onto many target meshes, caching the source
/// mesh's oriented bounding box so it is built once rather than once per target. This is the dominant cost when
/// matching a single prototype against a whole set of duplicates, so hoisting it out of the per-target loop is a
/// meaningful win. The result for a given target matches _getTransformFromToFuzzy with the same source and target.
class USD_OPTIMIZE_EXPORT FuzzyTransformSolver
{
public:
    FuzzyTransformSolver(const PXR_NS::VtVec3fArray& sourcePoints,
                         const PXR_NS::VtIntArray& sourceIndices,
                         const PXR_NS::VtIntArray& sourceFaceSizes);
    ~FuzzyTransformSolver();

    FuzzyTransformSolver(const FuzzyTransformSolver&) = delete;
    FuzzyTransformSolver& operator=(const FuzzyTransformSolver&) = delete;

    /// Transform that maps the source mesh's points onto the given target mesh's points (OBB to OBB).
    PXR_NS::GfMatrix4d computeTransformTo(const PXR_NS::VtVec3fArray& targetPoints,
                                          const PXR_NS::VtIntArray& targetIndices,
                                          const PXR_NS::VtIntArray& targetFaceSizes) const;

private:
    struct Impl;
    std::unique_ptr<Impl> m_impl;
};

USD_OPTIMIZE_EXPORT
void GetStageMeshDescriptors(std::vector<MeshTools::ClashMeshDescriptor>& meshDescriptors,
                             PXR_NS::SdfPathVector& paths,
                             const PXR_NS::UsdStageRefPtr& usdStage,
                             const std::vector<PXR_NS::UsdPrim>& prims);

} // namespace usd_optimize
