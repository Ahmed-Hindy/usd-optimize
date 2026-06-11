// SPDX-FileCopyrightText: Copyright (c) 2024-2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
// SPDX-License-Identifier: Apache-2.0
//

#include "DeletePrimsPlugin.h"

// Usd Optimize Core
#include <usd_optimize/core/Core.h>
#include <usd_optimize/core/RemovePrims.h>

PXR_NAMESPACE_USING_DIRECTIVE

// Register plugin
USD_OPTIMIZE_PLUGIN_INIT(usd_optimize::DeletePrimsOperation);


namespace usd_optimize
{

constexpr const char* s_category = "DELETE_PRIMS";

DeletePrimsOperation::DeletePrimsOperation()
    : Operation("deletePrims", "Delete Prims", "Deletes prims from a stage.")
{

    addArgument("primPaths", "Meshes To Process", kDisplayTypePrimPaths, "Optional list of prim paths to consider", m_primPaths)
        .setPlaceholder("Add meshes or all will be processed");
}


DeletePrimsOperation::~DeletePrimsOperation() = default;


bool DeletePrimsOperation::getVisible() const
{
    return false;
}


std::string DeletePrimsOperation::getAuthor() const
{
    return USD_OPTIMIZE_TO_STRING(USD_OPTIMIZE_PLUGIN_AUTHOR);
}


std::string DeletePrimsOperation::getCategory() const
{
    return s_category;
}


UsdOptimizePluginVersion DeletePrimsOperation::getVersion() const
{
    return { 1, 0, 0 };
}


OperationResult DeletePrimsOperation::executeImpl()
{
    _deletePrims(getUsdStage(), m_primPaths);
    return { true };
}


} // namespace usd_optimize
