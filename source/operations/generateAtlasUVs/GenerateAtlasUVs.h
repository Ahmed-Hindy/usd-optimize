// SPDX-FileCopyrightText: Copyright (c) 2023-2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
// SPDX-License-Identifier: Apache-2.0
//

#pragma once

// Usd Optimize Core
#include <usd_optimize/core/Defs.h>
#include <usd_optimize/core/Operation.h>

// C++
#include <mutex>


namespace usd_optimize
{

/// Generate atlas UVs using the boundary first flattening (BFF) algorithm.
class AtlasUVsOperation : public Operation
{
public:
    explicit AtlasUVsOperation();

    /// Get the author of this plugin
    std::string getAuthor() const override;

    /// Get the version of this plugin
    UsdOptimizePluginVersion getVersion() const override;

    /// Get the category for reporting.
    std::string getCategory() const override;

protected:
    OperationResult executeImpl() override;

private:
    std::vector<std::string> m_meshPrimPaths;
    double m_distortionThreshold;
    bool m_enableAtlasPacking;
    bool m_useWorldSpaceScales;
    double m_scaleFactor;
    double m_scaleUnits;
    bool m_overwriteExisting;
    std::mutex m_logMutex;
};

} // namespace usd_optimize
