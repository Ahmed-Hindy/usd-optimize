// SPDX-FileCopyrightText: Copyright (c) 2025-2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
// SPDX-License-Identifier: Apache-2.0
//

#pragma once

// Usd Optimize Core
#include <usd_optimize/core/Defs.h>
#include <usd_optimize/core/Operation.h>


namespace usd_optimize
{

/// Remove Attributes
///
/// A simple operation to remove user-specified attributes from prims.
class RemoveAttributesOperation : public Operation
{

    /// Operation to perform on matching attributes
    ///
    /// \ref Mode::eRemove Removes the property from the current edit target.
    /// \ref Mode::eBlock Authors a block, such that the attribute exists but has no value.
    enum class Mode
    {
        eRemove = 0, //< Remove the attribute
        eBlock = 1, //< Block the attribute
    };

public:
    /// Constructor
    RemoveAttributesOperation();

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

protected:
    /// Entry point
    OperationResult executeImpl() override;

private:
    Mode m_mode = Mode::eRemove;
    std::vector<std::string> m_primPaths;
    std::vector<std::string> m_attributes;
};


} // namespace usd_optimize
