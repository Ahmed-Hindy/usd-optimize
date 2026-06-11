// SPDX-FileCopyrightText: Copyright (c) 2020-2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
// SPDX-License-Identifier: Apache-2.0
//
#include "ComputeExtentsPlugin.h"

// Usd Optimize Core
#include <usd_optimize/core/ComputeExtents.h>
#include <usd_optimize/core/Core.h>
#include <usd_optimize/core/JsonUtils.h>
#include <usd_optimize/core/Log.h>


USD_OPTIMIZE_PLUGIN_INIT(usd_optimize::ComputeExtentsOperation);


namespace usd_optimize
{

constexpr const char* s_category = "COMPUTE_EXTENTS";

ComputeExtentsOperation::ComputeExtentsOperation()
    : Operation("computeExtents",
                "Compute Extents",
                "This will compute/recompute and author the ``extents`` property for meshes. If the paths "
                "argument is empty, all prims in the stage will be computed.")
{

    addArgument("paths", "Meshes To Process", kDisplayTypePrimPaths, "Optional list of prim paths to consider", m_primPaths)
        .setPlaceholder("Add meshes or all will be processed");
}


ComputeExtentsOperation::~ComputeExtentsOperation() = default;


std::string ComputeExtentsOperation::getAuthor() const
{
    return USD_OPTIMIZE_TO_STRING(USD_OPTIMIZE_PLUGIN_AUTHOR);
}


UsdOptimizePluginVersion ComputeExtentsOperation::getVersion() const
{
    return { 1, 0, 0 };
}


std::string ComputeExtentsOperation::getCategory() const
{
    return s_category;
}


std::string ComputeExtentsOperation::getDisplayGroup() const
{
    return s_displayGroupStage;
}


bool ComputeExtentsOperation::getSupportsAnalysis() const
{
    return true;
}


OperationResult ComputeExtentsOperation::executeImpl()
{
    const size_t numComputed = _computeExtents(getUsdStage(), m_primPaths);

    USD_OPTIMIZE_LOG_INFO("Computed extents for %zu prim%s", numComputed, numComputed == 1 ? "" : "s");

    return { true };
}


OperationResult ComputeExtentsOperation::executeAnalysisImpl()
{
    const std::vector<std::string> missing = _findPrimsMissingExtents(getUsdStage(), m_primPaths);

    PXR_NS::JsObject analysisResult;
    analysisResult["primsMissingExtent"] = _toJson(missing);

    PXR_NS::JsObject resultJson;
    resultJson["analysis"] = analysisResult;

    OperationResult result{ true };
    result.output = getCStr(PXR_NS::JsWriteToString(resultJson));
    return result;
}


} // namespace usd_optimize
