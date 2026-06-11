// SPDX-FileCopyrightText: Copyright (c) 2020-2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
// SPDX-License-Identifier: Apache-2.0
//

#pragma once

// Usd Optimize Core
#include <usd_optimize/core/Defs.h>
#include <usd_optimize/core/Operation.h>
#include <usd_optimize/core/UsdIncludes.h>


namespace usd_optimize
{

/// Generate Projection UVs
class DeletePrimsOperation : public Operation
{
public:
    /// Constructor
    explicit DeletePrimsOperation();

    /// Destructor
    ~DeletePrimsOperation() override;

    /// Set this operation invisible.
    bool getVisible() const override;

    /// Get the author of this plugin
    std::string getAuthor() const override;

    /// Get the version of this plugin
    UsdOptimizePluginVersion getVersion() const override;

    /// Get the reporting category
    std::string getCategory() const override;

protected:
    /// Entry-point for execution
    OperationResult executeImpl() override;

private:
    std::vector<std::string> m_primPaths;
};


} // namespace usd_optimize
