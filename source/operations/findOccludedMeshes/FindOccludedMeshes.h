// SPDX-FileCopyrightText: Copyright (c) 2020-2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
// SPDX-License-Identifier: Apache-2.0
//

#pragma once

// Usd Optimize Core
#include <usd_optimize/core/Defs.h>
#include <usd_optimize/core/Operation.h>
#include <usd_optimize/core/RemovePrims.h>

// C++
#include <string>
#include <vector>


namespace usd_optimize
{


/// Find hidden (occluded) meshes using MeshTools.
class FindOccludedMeshesOperation : public Operation
{
public:
    /// Constructor
    FindOccludedMeshesOperation();

    /// Get the long-form documentation for this plugin
    std::string getDocumentation() const override;

    /// Get the author of this plugin
    std::string getAuthor() const override;

    /// Get the version of this plugin
    UsdOptimizePluginVersion getVersion() const override;

    /// Get the category for reporting.
    std::string getCategory() const override;

    /// Support Analysis
    bool getSupportsAnalysis() const override;

protected:
    OperationResult executeImpl() override;

    /// Entry-point for analysis
    OperationResult executeAnalysisImpl() override;

private:
    std::vector<std::string> m_meshPrimPaths;
    bool m_clustered = true;
    float m_minimumGapSize = 0.01f;
    float m_maximumGridResolution = 500.0f;
    RemoveMethod m_action = RemoveMethod::eHide;
    bool m_checkTransparency = false;
    std::vector<std::string> m_attributePaths;
    bool m_useGpu = true;
};

} // namespace usd_optimize
