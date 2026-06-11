// SPDX-FileCopyrightText: Copyright (c) 2020-2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
// SPDX-License-Identifier: Apache-2.0
//

#pragma once

// Usd Optimize Core
#include <usd_optimize/core/Operation.h>


namespace usd_optimize
{


/// Analysis operation for finding USD Prims that have more than a specified number of children.
class FindFlatHierarchiesOperation : public Operation
{

public:
    /// Constructor
    explicit FindFlatHierarchiesOperation();

    /// Destructor
    ~FindFlatHierarchiesOperation() override;

    /// Get the author of this plugin
    std::string getAuthor() const override;

    /// Get the version of this plugin
    UsdOptimizePluginVersion getVersion() const override;

    /// Get the category for reporting.
    std::string getCategory() const override;

    /// Get the display group.
    std::string getDisplayGroup() const override;

    // Returns whether or not this operation supports analysis mode
    bool getSupportsAnalysis() const override;

protected:
    /// Entry-point for execution
    OperationResult executeImpl() override;

    /// Entry-point for analysis
    OperationResult executeAnalysisImpl() override;

private:
    std::vector<std::string> m_paths;
    // the number of children that will be considered a "flat" hierarchy
    int m_maxChildren = 500;
    // whether to consider all children or only active, loaded, defined, non-abstract children
    bool m_considerAllChildren = true;

    /// find and returns the prims that are considered flat hierarchies
    std::map<std::string, int> findFlatHierarchies();
};

} // namespace usd_optimize
