// SPDX-FileCopyrightText: Copyright (c) 2023-2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
// SPDX-License-Identifier: Apache-2.0
//
#include "MergeVertices.h"

// OmniMeshOps
#include <OmniMeshOps/Manifold.h>
#include <OmniMeshOps/UsdIO.h>

// Usd Optimize Core
#include <usd_optimize/core/Core.h>
#include <usd_optimize/core/Utils.h>

PXR_NAMESPACE_USING_DIRECTIVE

USD_OPTIMIZE_PLUGIN_INIT(usd_optimize::MergeVerticesOperation);


namespace usd_optimize
{

/// Constants
constexpr const char* s_categoryMergeVertices = "MERGEVERTICES";

MergeVerticesOperation::MergeVerticesOperation()
    : OmniOperation("mergeVertices",
                    "Merge Vertices",
                    "This operation merges vertices that are closer to one another than a given tolerance, "
                    "followed by removing any degenerate faces and optionally making the resulting mesh be manifold "
                    "and/or removing any isolated vertices.")
    , m_tolerance(0)
    , m_makeManifold(true)
    , m_removeIsolatedVertices(true)
    , m_mergeBoundaries(true)
{

    addArgument("paths", "Meshes To Process", kDisplayTypePrimPaths, "Optional list of prim paths to consider", m_meshPrimPaths)
        .setPlaceholder("Add meshes or all will be processed");

    addArgument(
        "tolerance",
        "Tolerance",
        kDisplayTypeFloatSlider,
        "The tolerance (distance) apart for vertices to be considered equal, a negative value skips the merge vertices step",
        m_tolerance);

    addArgument("mergeBoundaries",
                "Merge Boundaries",
                kDisplayTypeBool,
                "Merge boundaries when merging vertices",
                m_mergeBoundaries);

    addArgument("removeIsolatedVertices",
                "Remove isolated vertices",
                kDisplayTypeBool,
                "Removes isolated vertices (done after merging vertices)",
                m_removeIsolatedVertices);

    addArgument("makeManifold",
                "Make Manifold",
                kDisplayTypeBool,
                "Ensure the final result is a manifold mesh",
                m_makeManifold);
}


std::string MergeVerticesOperation::getAuthor() const
{
    return USD_OPTIMIZE_TO_STRING(USD_OPTIMIZE_PLUGIN_AUTHOR);
}


UsdOptimizePluginVersion MergeVerticesOperation::getVersion() const
{
    return { 2, 0, 0 };
}


std::string MergeVerticesOperation::getCategory() const
{
    return s_categoryMergeVertices;
}


std::string MergeVerticesOperation::getDisplayGroup() const
{
    return s_displayGroupGeometry;
}


bool MergeVerticesOperation::getVisible() const
{
    return false;
}

ProcessedData* MergeVerticesOperation::processMesh(const UsdPrim& prim, tbb::task_group_context&)
{

    using namespace omo;

    UsdGeomMesh usdMesh(prim);
    omo::CleanupOptions meshOptions{ omo::EnumSet{ omo::Defect::DegenerateEdges, omo::Defect::DegenerateFaces } };

    if (m_tolerance >= 0)
    {
        meshOptions.fixes += omo::Defect::CoincidentNeighborVertices;
        if (m_mergeBoundaries)
        {
            meshOptions.fixes += omo::Defect::CoincidentBoundaryVertices;
        }
        meshOptions.vertexMergeTolerance = m_tolerance;
    }

    if (m_removeIsolatedVertices)
    {
        meshOptions.fixes += omo::Defect::IsolatedVertices;
    }

    auto mesh = importMesh(usdMesh, meshOptions);
    if (m_makeManifold)
    {
        mesh = manifold(mesh);
    }

    auto result = new ProcessedHostMesh(mesh, prim);

    if (getContext()->verbose)
    {
        size_t beforeVertexCount = 0;
        VtVec3fArray points;
        if (usdMesh.GetPointsAttr().Get(&points))
        {
            beforeVertexCount = points.size();
        }

        std::string debugMessage = prim.GetName().GetString() + ": " + std::to_string(beforeVertexCount) + " -> " +
                                   std::to_string(result->vertexCount()) + " vertices";
        USD_OPTIMIZE_LOG_VERBOSE(debugMessage.c_str());
    }

    return result;
}


} // namespace usd_optimize
