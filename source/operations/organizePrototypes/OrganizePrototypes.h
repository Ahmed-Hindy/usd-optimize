// SPDX-FileCopyrightText: Copyright (c) 2024-2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
// SPDX-License-Identifier: Apache-2.0
//

#pragma once

// Usd Optimize Core
#include <usd_optimize/core/Defs.h>
#include <usd_optimize/core/Operation.h>
#include <usd_optimize/core/UsdIncludes.h>


namespace usd_optimize
{

/// Move internal instance prototypes to a user-specified namespace.
class OrganizePrototypesOperation : public Operation
{

public:
    /// Constructor
    explicit OrganizePrototypesOperation();

    /// Destructor
    ~OrganizePrototypesOperation() override;

    /// Get the author of this plugin
    std::string getAuthor() const override;

    /// Get the version of this plugin
    UsdOptimizePluginVersion getVersion() const override;

    /// Get the category for reporting.
    std::string getCategory() const override;

    /// Get the display group.
    std::string getDisplayGroup() const override;

protected:
    /// Entry-point for execution
    OperationResult executeImpl() override;

private:
    std::string m_protosNamespace;
    // Number of immediate prototype ancestors to preserve
    int m_hierarchyLevels;
};


} // namespace usd_optimize
