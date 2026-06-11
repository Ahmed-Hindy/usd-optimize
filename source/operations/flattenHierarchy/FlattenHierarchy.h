// SPDX-FileCopyrightText: Copyright (c) 2020-2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
// SPDX-License-Identifier: Apache-2.0
//

#pragma once

// Usd Optimize Core
#include <usd_optimize/core/Operation.h>


namespace usd_optimize
{

// Forward declarations
struct FlattenData;

class FlattenHierarchyOperation : public Operation
{
public:
    /// Constructor
    explicit FlattenHierarchyOperation();

    /// Get the author of this plugin
    std::string getAuthor() const override;

    /// Get the version of this plugin
    UsdOptimizePluginVersion getVersion() const override;

    /// Get the category for reporting.
    std::string getCategory() const override;

    /// Get the display group.
    std::string getDisplayGroup() const override;

    /// Returns whether this operation supports analysis mode.
    bool getSupportsAnalysis() const override;

protected:
    /// Entry-point for execution
    OperationResult executeImpl() override;

    /// Entry-point for analysis
    OperationResult executeAnalysisImpl() override;

private:
    void reparent(const PXR_NS::SdfPath& from, const PXR_NS::SdfPath& to, FlattenData& flattenData) const;
    void traversePrim(const PXR_NS::UsdPrim& prim, const PXR_NS::UsdPrim& target, FlattenData& flattenData) const;
    void fixOriginalData(const FlattenData& flattenData) const;
    void fixOriginalMaterials(const FlattenData& flattenData) const;

    std::vector<std::string> m_primPaths;
    bool m_identityOnly = false;
};


} // namespace usd_optimize
