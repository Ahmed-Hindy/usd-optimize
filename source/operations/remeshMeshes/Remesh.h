// SPDX-FileCopyrightText: Copyright (c) 2020-2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
// SPDX-License-Identifier: Apache-2.0
//

#pragma once

// Usd Optimize Core
#include <usd_optimize/core/Defs.h>
#include <usd_optimize/core/OmniOperation.h>


namespace usd_optimize
{

/// Remesh meshes using OmniMesh.
class RemeshOperation : public OmniOperation
{
public:
    RemeshOperation();

    ~RemeshOperation() override;

    /// Get the author of this operation
    std::string getAuthor() const override;

    /// Get the version of this plugin
    UsdOptimizePluginVersion getVersion() const override;

    /// Get the category for reporting.
    std::string getCategory() const override;

    /// Get the display group.
    std::string getDisplayGroup() const override;

protected:
    /// Process
    ProcessedData* processMesh(const PXR_NS::UsdPrim& prim, tbb::task_group_context& taskGroupContext) override;

private:
    double m_gradation;
    double m_maxError;
    unsigned int m_gpu_vertexcount_threshold;
};

} // namespace usd_optimize
