// SPDX-FileCopyrightText: Copyright (c) 2025-2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
// SPDX-License-Identifier: Apache-2.0
//

#pragma once

// Usd Optimize Core
#include <usd_optimize/core/Defs.h>
#include <usd_optimize/core/Operation.h>

namespace usd_optimize
{

/// Count Vertices
///
/// Determine the vertex count of prims and produce output noting anything over the configured
/// thresholds.
class CountVerticesOperation : public Operation
{

public:
    /// Constructor
    CountVerticesOperation();

    /// Get the author of this plugin
    std::string getAuthor() const override;

    /// Get the version of this plugin
    UsdOptimizePluginVersion getVersion() const override;

    /// Get the category for reporting.
    std::string getCategory() const override;

    /// Get whether operation is visible
    bool getVisible() const override;

    /// Support analysis
    bool getSupportsAnalysis() const override;

protected:
    /// Entry point
    OperationResult executeImpl() override;

    /// Entry point for analysis
    OperationResult executeAnalysisImpl() override;

private:
    uint64_t m_levelHigh = 100000;
    uint64_t m_levelVeryHigh = 500000;
    uint64_t m_levelExtreme = 1000000;
};


} // namespace usd_optimize
