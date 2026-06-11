// SPDX-FileCopyrightText: Copyright (c) 2020-2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
// SPDX-License-Identifier: Apache-2.0
//

#include "Triangulate.h"

// Usd Optimize Core
#include <usd_optimize/core/Core.h>
#include <usd_optimize/core/CudaUtils.h>
#include <usd_optimize/core/Utils.h>

// OmniMesh
#include <OmniMeshOps/ScopedCudaContext.h>
#include <OmniMeshOps/Triangulate.h>
#include <OmniMeshOps/usd/Mesh.h>

PXR_NAMESPACE_USING_DIRECTIVE

USD_OPTIMIZE_PLUGIN_INIT(usd_optimize::TriangulateOperation);


namespace usd_optimize
{

/// Constants
constexpr const char* s_categoryTriangulate = "TRIANGULATE";

TriangulateOperation::TriangulateOperation()
    : OmniOperation("triangulateMeshes", "Triangulate Meshes", "This operation triangulates meshes.")
    , m_gpu_vertexcount_threshold(1000000)
{

    addArgument("paths",
                "Meshes to triangulate",
                kDisplayTypePrimPaths,
                "Optional list of prim paths to consider",
                m_meshPrimPaths)
        .setPlaceholder("Add meshes or all will be processed");

    addArgument("gpuVertexCountThreshold",
                "GPU vertex count threshold",
                kDisplayTypeInt,
                "When a mesh has more than this number of vertices, use GPU algorithm",
                m_gpu_vertexcount_threshold)
        .setMin(0)
        .setVisible(false);
}


std::string TriangulateOperation::getAuthor() const
{
    return USD_OPTIMIZE_TO_STRING(USD_OPTIMIZE_PLUGIN_AUTHOR);
}


UsdOptimizePluginVersion TriangulateOperation::getVersion() const
{
    return { 1, 0, 0 };
}


std::string TriangulateOperation::getCategory() const
{
    return s_categoryTriangulate;
}


std::string TriangulateOperation::getDisplayGroup() const
{
    return s_displayGroupGeometry;
}


ProcessedData* TriangulateOperation::processMesh(const UsdPrim& prim, tbb::task_group_context&)
{
    using namespace omo;

    ProcessedData* result = nullptr;
    UsdGeomMesh usdMesh(prim);
    omo::usd::HostMesh inputMesh{ usdMesh };

    auto use_gpu_triangulator = inputMesh.vertexCount() > m_gpu_vertexcount_threshold && isCudaAvailable();
    if (!use_gpu_triangulator)
    {
        HostTriangulate triangulate{ inputMesh };
        auto triMesh = triangulate();
        result = new ProcessedHostMesh(triMesh, prim);
    }
    else
    {
        ScopedCudaContext cuda_context(omo::Verbose{ getContext()->verbose > 0 });
        DeviceTriangulate deviceTriangulate{ DeviceMesh{ inputMesh } };
        HostMesh hostTriMesh(deviceTriangulate());
        result = new ProcessedHostMesh(hostTriMesh, prim);
    }

    return result;
}

} // namespace usd_optimize
