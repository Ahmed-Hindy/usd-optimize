// SPDX-FileCopyrightText: Copyright (c) 2020-2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
// SPDX-License-Identifier: Apache-2.0
//

#pragma once

// Usd Optimize Core
#include <usd_optimize/core/Defs.h>
#include <usd_optimize/core/Operation.h>
#include <usd_optimize/core/UsdIncludes.h>
#include <usd_optimize/core/geometry/DeduplicateUtils.h>


namespace usd_optimize
{


/// Find groups of coinciding prims.
class FindCoincidingGeometryOperation : public Operation
{
public:
    /// Constructor
    explicit FindCoincidingGeometryOperation();

    /// Get the author of this plugin
    std::string getAuthor() const override;

    /// Get the version of this plugin
    UsdOptimizePluginVersion getVersion() const override;

    /// Get the category for reporting.
    std::string getCategory() const override;

    // Returns whether this operation supports analysis mode
    bool getSupportsAnalysis() const override;

protected:
    /// Entry-point for execution
    OperationResult executeImpl() override;

    /// Entry-point for analysis
    OperationResult executeAnalysisImpl() override;

private:
    PrimVectors computeCoincidingGeometry(const PrimVectors& equalMeshPrimSets);

    std::vector<std::string> m_paths;
    float m_tolerance = 0.001f;
    float m_offset = 0.0f;
    bool m_fuzzy = false;
    std::vector<std::vector<PXR_NS::UsdPrim>> m_coincidingPrims;
};


} // namespace usd_optimize
