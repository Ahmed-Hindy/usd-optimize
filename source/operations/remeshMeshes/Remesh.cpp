// SPDX-FileCopyrightText: Copyright (c) 2020-2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
// SPDX-License-Identifier: Apache-2.0
//

#include "Remesh.h"

// Usd Optimize Core
#include <usd_optimize/core/Core.h>
#include <usd_optimize/core/CudaUtils.h>
#include <usd_optimize/core/Utils.h>

// OmniMesh
#include <OmniMeshOps/Remesh.h>
#include <OmniMeshOps/ScopedCudaContext.h>
#include <OmniMeshOps/UsdIO.h>

PXR_NAMESPACE_USING_DIRECTIVE

// Register plugin with Usd Optimize
USD_OPTIMIZE_PLUGIN_INIT(usd_optimize::RemeshOperation);


namespace usd_optimize
{

/// Constants
constexpr const char* s_categoryRemesh = "REMESH";

RemeshOperation::RemeshOperation()
    : OmniOperation("remeshMeshes", "Remesh Meshes", "Remesh existing mesh prims to user defined tolerance.")
    , m_gradation(0)
    , m_maxError(0.1)
    , m_gpu_vertexcount_threshold(500000)
{
    addArgument("paths",
                "Meshes to Remesh",
                kDisplayTypePrimPaths,
                "Optional list of prim paths/expressions to remesh",
                m_meshPrimPaths)
        .setPlaceholder("Add meshes or all will be processed");

    addArgument(
        "gradation",
        "Gradation",
        kDisplayTypeFloatSlider,
        "The gradation for the remesh, affecting how many triangles are generated. [Note: this parameter will likely be replaced by something else]",
        m_gradation)
        .setMin(0)
        .setMax(0.5);

    addArgument("maxError", "Maximum Error", kDisplayTypeFloatSlider, "Maximum error for the remesh.", m_maxError).setMin(0);

    addArgument("gpuVertexCountThreshold",
                "GPU Vertex Threshold",
                kDisplayTypeIntSlider,
                "Use GPU algorithm if vertex count is greater than this value",
                m_gpu_vertexcount_threshold)
        .setMin(0)
        .setVisible(false);
}


RemeshOperation::~RemeshOperation(){};


std::string RemeshOperation::getDocumentation() const
{
    return "This operation will remesh input mesh prims to a defined tolerance "
           "to create a new mesh topology. Input mesh and normals will guide "
           "the maximum error and size of the triangles to match input volume.";
}


std::string RemeshOperation::getAuthor() const
{
    return USD_OPTIMIZE_TO_STRING(USD_OPTIMIZE_PLUGIN_AUTHOR);
}


UsdOptimizePluginVersion RemeshOperation::getVersion() const
{
    return { 1, 0, 0 };
}


std::string RemeshOperation::getCategory() const
{
    return s_categoryRemesh;
}


std::string RemeshOperation::getDisplayGroup() const
{
    return s_displayGroupGeometry;
}


ProcessedData* RemeshOperation::processMesh(const UsdPrim& prim, tbb::task_group_context& taskGroupContext)
{
    using namespace omo;

    ProcessedData* result = nullptr;

    try
    {
        UsdGeomMesh usdMesh(prim);

        // Validate topology and geometry before handing the mesh to the native remesher. Malformed
        // topology (out-of-range indices, count/index mismatch) or non-finite (NaN/Inf) coordinates
        // make it flood assertion failures and return garbage while still reporting success -- skip
        // such meshes instead.
        VtVec3fArray points;
        usdMesh.GetPointsAttr().Get(&points);
        VtIntArray faceVertexIndices;
        usdMesh.GetFaceVertexIndicesAttr().Get(&faceVertexIndices);
        VtIntArray faceVertexCounts;
        usdMesh.GetFaceVertexCountsAttr().Get(&faceVertexCounts);

        std::string topologyMsg;
        if (!usdMesh.ValidateTopology(faceVertexIndices.AsConst(), faceVertexCounts.AsConst(), points.size(), &topologyMsg))
        {
            USD_OPTIMIZE_LOG_WARN("Prim: %s has invalid topology:\n %s",
                                  prim.GetPath().GetAsString().c_str(),
                                  topologyMsg.c_str());
            return nullptr;
        }

        if (!arePointsFinite(points))
        {
            USD_OPTIMIZE_LOG_WARN("Prim: %s has non-finite point coordinates; skipping.",
                                  prim.GetPath().GetAsString().c_str());
            return nullptr;
        }

        VtVec3fArray normals;
        if (usdMesh.GetNormalsAttr().Get(&normals) && !arePointsFinite(normals))
        {
            USD_OPTIMIZE_LOG_WARN("Prim: %s has non-finite normals; skipping.", prim.GetPath().GetAsString().c_str());
            return nullptr;
        }

        // A non-finite world transform (e.g. a NaN in a parent xform) resolves to non-finite
        // world-space geometry even though the authored local points are finite; remesh otherwise
        // bakes an all-NaN transform onto the output and still reports success.
        if (!isTransformFinite(usdMesh.ComputeLocalToWorldTransform(UsdTimeCode::Default())))
        {
            USD_OPTIMIZE_LOG_WARN("Prim: %s has a non-finite transform; skipping.", prim.GetPath().GetAsString().c_str());
            return nullptr;
        }

        auto inputMesh = importMesh(usdMesh, { omo::manifestDefects + omo::Defect::CoincidentBoundaryVertices });

        auto use_gpu = inputMesh.vertexCount() > m_gpu_vertexcount_threshold && isCudaAvailable();
        if (!use_gpu)
        {
            HostRemesh remesh(inputMesh);
            {
                if (!taskGroupContext.is_group_execution_cancelled())
                {
                    auto remeshed_mesh = remesh(m_gradation, m_maxError);
                    if (!taskGroupContext.is_group_execution_cancelled())
                    {
                        result = new ProcessedHostMesh(remeshed_mesh, prim);
                    }
                }
            }
        }
        else
        {
            ScopedCudaContext cuda_context(omo::Verbose{ getContext()->verbose > 0 });
            DeviceRemesh device_remesh{ DeviceMesh{ inputMesh } };

            if (!taskGroupContext.is_group_execution_cancelled())
            {
                HostMesh host_remeshed_mesh(device_remesh(m_gradation, m_maxError));
                if (!taskGroupContext.is_group_execution_cancelled())
                {
                    result = new ProcessedHostMesh(host_remeshed_mesh, prim);
                }
            }
        }

        if (result != nullptr)
        {
            std::ostringstream oss;
            oss << prim.GetName().GetString() << ": "
                << "\nBefore:  Faces: " << inputMesh.faceCount() << "  Vertices: " << inputMesh.vertexCount()
                << "\nAfter:  Faces: " << result->faceCount() << "  Vertices: " << result->vertexCount();
            USD_OPTIMIZE_LOG_VERBOSE(oss.str().c_str());
        }
    }
    catch (const std::exception& e)
    {
        std::string errorMsg = std::string(e.what()) + " (Prim: " + prim.GetPath().GetText() + ")";
        USD_OPTIMIZE_LOG_ERROR(errorMsg.c_str());
        if (result)
        {
            delete result;
            result = nullptr;
        }

        // Cancel further task execution
        if (taskGroupContext.cancel_group_execution())
        {
            USD_OPTIMIZE_LOG_ERROR("Cancelling execution due to exception...");
        }
    }

    if (result != nullptr && taskGroupContext.is_group_execution_cancelled())
    {
        delete result;
        result = nullptr;
    }

    return result;
}


} // namespace usd_optimize
