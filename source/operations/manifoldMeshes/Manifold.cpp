// SPDX-FileCopyrightText: Copyright (c) 2023-2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
// SPDX-License-Identifier: Apache-2.0
//
#include "Manifold.h"

// Usd Optimize Core
#include <usd_optimize/core/Core.h>
#include <usd_optimize/core/Utils.h>

// OmniMeshOps
#include <OmniMeshOps/Manifold.h>
#include <OmniMeshOps/UsdIO.h>

PXR_NAMESPACE_USING_DIRECTIVE

USD_OPTIMIZE_PLUGIN_INIT(usd_optimize::ManifoldOperation);


namespace usd_optimize
{

/// Constants
constexpr const char* s_categoryManifold = "MANIFOLD";

ManifoldOperation::ManifoldOperation()
    : OmniOperation("manifoldMeshes", "Manifold Meshes", "Makes mesh Manifold.")
{

    addArgument("paths", "Meshes To Process", kDisplayTypePrimPaths, "Optional list of prim paths to consider", m_meshPrimPaths)
        .setPlaceholder("Add meshes or all will be processed");
}


std::string ManifoldOperation::getAuthor() const
{
    return USD_OPTIMIZE_TO_STRING(USD_OPTIMIZE_PLUGIN_AUTHOR);
}


UsdOptimizePluginVersion ManifoldOperation::getVersion() const
{
    return { 1, 0, 0 };
}


std::string ManifoldOperation::getCategory() const
{
    return s_categoryManifold;
}


std::string ManifoldOperation::getDisplayGroup() const
{
    return s_displayGroupGeometry;
}


ProcessedData* ManifoldOperation::processMesh(const UsdPrim& prim, tbb::task_group_context&)
{
    using namespace omo;

    ProcessedData* result = nullptr;

    try
    {
        UsdGeomMesh usdMesh(prim);
        auto mesh = importMesh(usdMesh, { omo::noDefects });

        size_t srcVertexCount = mesh.vertexCount();

        mesh = manifold(mesh);

        // The GPU manifold code here was removed due to being slower than running it on CPU.
        // The host<->device mesh copying took longer than the manifold operation itself.
        result = new ProcessedHostMesh(mesh, prim);

        USD_OPTIMIZE_LOG_VERBOSE("%s: %u -> %u vertices", prim.GetName().GetText(), srcVertexCount, mesh.vertexCount());
    }
    catch (const std::exception& e)
    {
        std::string errorMsg = prim.GetPath().GetAsString() + ": " + std::string(e.what());
        USD_OPTIMIZE_LOG_ERROR(errorMsg.c_str());
        if (result)
        {
            delete result;
            result = nullptr;
        }
    }

    return result;
}

} // namespace usd_optimize
