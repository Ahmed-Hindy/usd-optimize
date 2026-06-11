// SPDX-FileCopyrightText: Copyright (c) 2020-2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
// SPDX-License-Identifier: Apache-2.0
//

#pragma once

// Usd Optimize Core
#include <usd_optimize/core/Defs.h>
#include <usd_optimize/core/OmniOperation.h>


namespace usd_optimize
{

enum class DecimateGuideOption
{
    eByNormals, // Use normals to guide decimation
    eByColors, // Use per-vertex colors to guide decimation
    eOff, // Disable attribute-guided decimation
};

/// Decimate meshes using OmniMesh.
class DecimateOperation : public OmniOperation
{
public:
    DecimateOperation();

    ~DecimateOperation() override;

    /// Get the author of this operation
    std::string getAuthor() const override;

    /// Get the version of this plugin
    UsdOptimizePluginVersion getVersion() const override;

    /// Get the category for reporting.
    std::string getCategory() const override;

    /// Get the display group.
    std::string getDisplayGroup() const override;

protected:
    /// The predicate used to resolve prim expressions in executeImpl()
    PXR_NS::Usd_PrimFlagsPredicate primFlagsPredicate() const override
    {
        // This is UsdPrimDefaultPredicate without !UsdPrimIsAbstract, so abstract prims will be processed.
        return PXR_NS::UsdPrimIsActive && PXR_NS::UsdPrimIsDefined && PXR_NS::UsdPrimIsLoaded;
    }

    /// Process
    ProcessedData* processMesh(const PXR_NS::UsdPrim& prim, tbb::task_group_context&) override;

    /// Pre
    OperationResult executePre() override;

    /// Post
    void executePost(const TotalStats& totalStats) override;

private:
    double m_reductionFactor;
    double m_maxMeanError;
    double m_minFeatureArea;
    double m_featureSensitivity;
    unsigned int m_cpuVertexcountThreshold;
    unsigned int m_gpuVertexcountThreshold;
    DecimateGuideOption m_guideDecimation;
    bool m_pinBoundaries;
    bool m_allowCutAndGlue;
};

} // namespace usd_optimize
