// SPDX-FileCopyrightText: Copyright (c) 2020-2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
// SPDX-License-Identifier: Apache-2.0
//

#pragma once

// Usd Optimize Core
#include <usd_optimize/core/Operation.h>


namespace usd_optimize
{

class OptimizeSkelRootsOperation : public Operation
{
public:
    /// Constructor
    explicit OptimizeSkelRootsOperation();

    /// Get the documentation string for this plugin.
    std::string getDocumentation() const override;

    /// Get the author of this plugin
    std::string getAuthor() const override;

    /// Get the version of this plugin
    UsdOptimizePluginVersion getVersion() const override;

    std::string getCategory() const override;

protected:
    /// Entry-point for execution
    OperationResult executeImpl() override;
};

} // namespace usd_optimize
