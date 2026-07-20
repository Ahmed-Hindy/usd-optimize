// SPDX-FileCopyrightText: Copyright (c) 2020-2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
// SPDX-License-Identifier: Apache-2.0
//

#pragma once

// Usd Optimize Core
#include <usd_optimize/core/Operation.h>
#include <usd_optimize/core/UsdIncludes.h>
#include <usd_optimize/core/geometry/SpatialClustering.h>


namespace usd_optimize
{

/// Custom userdata for inter-plugin communication
struct MergeUserData
{
    // Input
    BucketerPtr bucketer = nullptr;
    bool considerSkeleton = false;

    // Output
    std::vector<PXR_NS::UsdPrim> mergedPrims;
};


/// Merge Static Meshes Operation
///
/// Usd Optimize Operation to combine individual Usd Meshes in to one larger merged mesh.
class MergeOperation : public Operation
{

public:
    /// Constructor
    explicit MergeOperation();

    /// Destructor
    ~MergeOperation() override;

    /// Get the documentation string for this plugin.
    std::string getDocumentation() const override;

    /// Get the author of this plugin
    std::string getAuthor() const override;

    /// Get the version of this plugin
    UsdOptimizePluginVersion getVersion() const override;

    /// Get the category for reporting.
    std::string getCategory() const override;

    /// Get the display group.
    std::string getDisplayGroup() const override;

    /// Set custom user data.
    ///
    /// Expects a pointer to a valid \ref MergeUserData object.
    ///
    /// \param userData
    void setUserData(void* userData) override;

protected:
    /// Entry-point for execution
    OperationResult executeImpl() override;


private:
    std::vector<std::string> m_meshPrimPaths;

    // spatial clustering helper
    SpatialClustering m_clustering;

    MergeUserData* m_userData = nullptr;
};


} // namespace usd_optimize
