// SPDX-FileCopyrightText: Copyright (c) 2020-2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
// SPDX-License-Identifier: Apache-2.0
//

#pragma once

// Usd Optimize Core
#include <usd_optimize/core/OmniOperation.h>


namespace usd_optimize
{

/// Merge vertices using OmniMesh.
class MergeVerticesOperation : public OmniOperation
{
public:
    MergeVerticesOperation();

    /// Get the author of this plugin
    std::string getAuthor() const override;

    /// Get the version of this plugin
    UsdOptimizePluginVersion getVersion() const override;

    /// Get the category for reporting.
    std::string getCategory() const override;

    /// Get the display group.
    std::string getDisplayGroup() const override;

    /// Hide operation in UI
    bool getVisible() const override;

protected:
    ProcessedData* processMesh(const PXR_NS::UsdPrim& prim, tbb::task_group_context&);

private:
    float m_tolerance;
    bool m_makeManifold;
    bool m_removeIsolatedVertices;
    bool m_mergeBoundaries;
};

} // namespace usd_optimize
