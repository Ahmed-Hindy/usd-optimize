// SPDX-FileCopyrightText: Copyright (c) 2020-2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
// SPDX-License-Identifier: Apache-2.0
//

#include "usd_optimize/core/MeshToolsCommon.h"

// MeshTools
#include <MeshTools/Geometry.h>
#include <MeshTools/Math.h>
#include <MeshTools/Stage.h>
#include <MeshTools/VisCheckerCPU.h>

// USD
#include <pxr/usd/usd/primRange.h>
#include <pxr/usd/usdGeom/primvarsAPI.h>
#include <pxr/usd/usdShade/shader.h>

using namespace MeshTools;
PXR_NAMESPACE_USING_DIRECTIVE


namespace usd_optimize
{


static void convert(const VtVec3fArray& source, std::vector<Vec3>& target, GfMatrix4d* globalTransform = nullptr)
{
    target.resize(source.size());

    for (size_t i = 0; i < source.size(); i++)
    {
        GfVec3d point = globalTransform ? globalTransform->Transform(source[i]) : source[i];
        target[i].set(point[0], point[1], point[2]);
    }
}


static void convert(const VtIntArray& source, std::vector<int>& target)
{
    target.resize(source.size());

    for (size_t i = 0; i < source.size(); i++)
    {
        target[i] = source[i];
    }
}


bool _isTransparent(const UsdPrim& prim, UsdTimeCode time = UsdTimeCode::Default())
{
    // 1. Check generic renderable geometry (covers Mesh, Curves, Points)
    if (prim.IsA<UsdGeomGprim>())
    {
        UsdGeomPrimvarsAPI primvarsAPI(prim);
        UsdGeomPrimvar opacityPrimvar = primvarsAPI.GetPrimvar(UsdGeomTokens->primvarsDisplayOpacity);

        if (opacityPrimvar)
        {
            VtValue val;
            if (opacityPrimvar.Get(&val, time))
            {
                if (val.IsArrayValued() && val.IsHolding<VtFloatArray>())
                {
                    for (float v : val.UncheckedGet<VtFloatArray>())
                    {
                        if (v < 1.0f)
                        {
                            return true;
                        }
                    }
                }
            }
        }
    }

    // 2. Material Binding
    UsdShadeMaterialBindingAPI bindingAPI(prim);
    UsdShadeMaterial boundMaterial = bindingAPI.ComputeBoundMaterial();
    if (!boundMaterial)
    {
        return false;
    }

    // 3. Surface Output
    UsdShadeOutput surfaceOutput = boundMaterial.GetSurfaceOutput();
    if (!surfaceOutput)
    {
        return false;
    }

    // 4. Trace Connection to Shader
    UsdShadeConnectableAPI connectedSource;
    TfToken connectedSourceName;
    UsdShadeAttributeType connectedSourceType;

    if (!surfaceOutput.GetConnectedSource(&connectedSource, &connectedSourceName, &connectedSourceType))
    {
        return false;
    }

    UsdShadeShader surfaceShader(connectedSource.GetPrim());
    if (!surfaceShader)
    {
        return false;
    }

    // 5. Check Opacity Input
    UsdShadeInput opacityInput = surfaceShader.GetInput(TfToken("opacity"));

    if (opacityInput)
    {
        float opacityValue = 1.0f;
        if (opacityInput.Get(&opacityValue, time))
        {
            // Use a small epsilon for float comparison safety
            return opacityValue < 0.999f;
        }
    }

    return false;
}


std::shared_ptr<Mesh> _GetMesh(const UsdPrim& prim, UsdGeomXformCache& xformCache, bool checkTransparency = false)
{
    std::vector<Vec3> vertices;
    std::vector<int> indices;
    std::vector<int> faceSizes;

    VtVec3fArray points;
    VtIntArray faceVertexIndices;
    VtIntArray faceVertexCounts;

    if (!prim.IsA<UsdGeomMesh>())
    {
        return nullptr;
    }

    // The user can specify meshes to not be considered as occluders
    // by setting them to invisible using the USD visibility attribute

    auto visAttr = prim.GetAttribute(UsdGeomTokens->visibility);

    if (visAttr)
    {
        TfToken token;
        visAttr.Get(&token, UsdTimeCode::Default());

        if (token == UsdGeomTokens->invisible)
        {
            return nullptr;
        }
    }

    // Skip transparent meshes if requested, as they should not be occluders
    if (checkTransparency && _isTransparent(prim))
    {
        return nullptr;
    }


    UsdGeomXformable xformable(prim);

    UsdGeomMesh usdMesh(prim);

    std::shared_ptr<Mesh> mesh(new Mesh());

    mesh->setPath(prim.GetPath().GetString());

    GfMatrix4d globalTransform = xformCache.GetLocalToWorldTransform(prim);

    vertices.clear();
    indices.clear();
    faceSizes.clear();

    // get the points

    UsdAttribute pointsAttr = usdMesh.GetPointsAttr();

    if (pointsAttr.Get(&points, UsdTimeCode::Default()))
    {
        convert(points, vertices, &globalTransform);
    }

    mesh->setVertices(vertices);

    // get the indices

    UsdAttribute faceVertexIndicesAttr = usdMesh.GetFaceVertexIndicesAttr();

    if (faceVertexIndicesAttr.Get(&faceVertexIndices, UsdTimeCode::Default()))
    {
        convert(faceVertexIndices, indices);
    }

    mesh->setIndices(indices);

    // get the face sizes

    UsdAttribute faceVertexCountsAttr = usdMesh.GetFaceVertexCountsAttr();

    if (faceVertexCountsAttr.Get(&faceVertexCounts, UsdTimeCode::Default()))
    {
        convert(faceVertexCounts, faceSizes);
    }

    mesh->setFaceSizes(faceSizes);

    return mesh;
}


std::shared_ptr<Stage> GetStage(const UsdStageRefPtr& usdStage,
                                const std::vector<UsdPrim>& prims,
                                bool ignoreTransparentMeshes)
{
    UsdGeomXformCache xformCache(0.0);

    std::vector<std::shared_ptr<Mesh>> meshes;

    if (prims.empty())
    {
        for (const auto& prim : usdStage->Traverse())
        {
            auto mesh = _GetMesh(prim, xformCache, ignoreTransparentMeshes);

            if (mesh)
            {
                meshes.push_back(mesh);
            }
        }
    }
    else
    {
        for (const auto& prim : prims)
        {
            auto mesh = _GetMesh(prim, xformCache, ignoreTransparentMeshes);

            if (mesh)
            {
                meshes.push_back(mesh);
            }
        }
    }

    auto stage = std::make_shared<Stage>();

    if (!meshes.empty())
    {
        stage->init(meshes);
    }

    return stage;
}


// Compute the oriented bounding box of a mesh given as USD point/topology arrays.
static OBB _computeMeshOBB(const VtVec3fArray& points, const VtIntArray& indices, const VtIntArray& faceSizes)
{
    std::vector<Vec3> vertices;
    std::vector<int> ids;
    std::vector<int> sizes;

    convert(points, vertices);
    convert(indices, ids);
    convert(faceSizes, sizes);

    // If true, optimizes towards the volume minimizing OBB using multiple 2d projections.
    // This increases the computation time.
    constexpr bool optimizeOBB = true;

    return computeOBBFromSurface(vertices, ids, sizes, optimizeOBB);
}


// Convert the affine OBB-to-OBB transform into a USD matrix.
static GfMatrix4d _obbToObbMatrix(const OBB& sourceOBB, const OBB& targetOBB)
{
    AffineTransform transform;
    getObbToObbTransform(sourceOBB, targetOBB, transform);

    Vec4 c0(transform.A.column0, 0.0f);
    Vec4 c1(transform.A.column1, 0.0f);
    Vec4 c2(transform.A.column2, 0.0f);
    Vec4 c3(transform.b, 1.0f);

    return GfMatrix4d(c0[0],
                      c0[1],
                      c0[2],
                      c0[3],
                      c1[0],
                      c1[1],
                      c1[2],
                      c1[3],
                      c2[0],
                      c2[1],
                      c2[2],
                      c2[3],
                      c3[0],
                      c3[1],
                      c3[2],
                      c3[3]);
}


GfMatrix4d _getTransformFromToFuzzy(const PXR_NS::VtVec3fArray& sourcePoints,
                                    const PXR_NS::VtIntArray& sourceIndices,
                                    const PXR_NS::VtIntArray& sourceFaceSizes,
                                    const PXR_NS::VtVec3fArray& targetPoints,
                                    const PXR_NS::VtIntArray& targetIndices,
                                    const PXR_NS::VtIntArray& targetFaceSizes)
{
    const OBB sourceOBB = _computeMeshOBB(sourcePoints, sourceIndices, sourceFaceSizes);
    const OBB targetOBB = _computeMeshOBB(targetPoints, targetIndices, targetFaceSizes);
    return _obbToObbMatrix(sourceOBB, targetOBB);
}


struct FuzzyTransformSolver::Impl
{
    OBB sourceOBB;
};


FuzzyTransformSolver::FuzzyTransformSolver(const VtVec3fArray& sourcePoints,
                                           const VtIntArray& sourceIndices,
                                           const VtIntArray& sourceFaceSizes)
    : m_impl(new Impl{ _computeMeshOBB(sourcePoints, sourceIndices, sourceFaceSizes) })
{
}


FuzzyTransformSolver::~FuzzyTransformSolver() = default;


GfMatrix4d FuzzyTransformSolver::computeTransformTo(const VtVec3fArray& targetPoints,
                                                    const VtIntArray& targetIndices,
                                                    const VtIntArray& targetFaceSizes) const
{
    const OBB targetOBB = _computeMeshOBB(targetPoints, targetIndices, targetFaceSizes);
    return _obbToObbMatrix(m_impl->sourceOBB, targetOBB);
}

bool _GetMeshDescriptor(ClashMeshDescriptor& meshDesc, const UsdPrim& prim, UsdGeomXformCache& xformCache)
{
    // Initialize to ensure deterministic cleanup
    meshDesc.vertices = nullptr;
    meshDesc.numVertices = 0;
    meshDesc.indices = nullptr;
    meshDesc.numIndices = 0;
    meshDesc.faceSizes = nullptr;
    meshDesc.numFaces = 0;
    meshDesc.transform = Mat44d(MeshTools::Zero);
    meshDesc.groupId = 0;

    if (!prim.IsA<UsdGeomMesh>())
    {
        return false;
    }

    // The user can specify meshes to not be considered as occluders
    // by setting them to invisible using the USD visibility attribute

    auto visAttr = prim.GetAttribute(UsdGeomTokens->visibility);

    if (visAttr)
    {
        TfToken token;
        visAttr.Get(&token, UsdTimeCode::Default());

        if (token == UsdGeomTokens->invisible)
        {
            return false;
        }
    }

    UsdGeomMesh usdMesh(prim);

    // get the points

    UsdAttribute pointsAttr = usdMesh.GetPointsAttr();
    VtVec3fArray points;

    if (!pointsAttr.Get(&points, UsdTimeCode::Default()) || points.empty())
    {
        return false;
    }
    else
    {
        meshDesc.numVertices = (int)points.size();
        auto vertices = new Vec3[meshDesc.numVertices];

        for (int i = 0; i < meshDesc.numVertices; i++)
        {
            GfVec3d point = points[i];
            vertices[i].set(point[0], point[1], point[2]);
        }

        meshDesc.vertices = vertices;
    }

    // get the indices

    UsdAttribute faceVertexIndicesAttr = usdMesh.GetFaceVertexIndicesAttr();
    VtIntArray faceVertexIndices;

    if (!faceVertexIndicesAttr.Get(&faceVertexIndices, UsdTimeCode::Default()) || faceVertexIndices.empty())
    {
        delete[] meshDesc.vertices;
        meshDesc.vertices = nullptr;
        return false;
    }
    else
    {
        meshDesc.numIndices = (int)faceVertexIndices.size();
        auto indices = new int[meshDesc.numIndices];

        for (int i = 0; i < meshDesc.numIndices; i++)
        {
            indices[i] = faceVertexIndices[i];
        }

        meshDesc.indices = indices;
    }

    // get the face sizes

    UsdAttribute faceVertexCountsAttr = usdMesh.GetFaceVertexCountsAttr();
    VtIntArray faceVertexCounts;

    if (!faceVertexCountsAttr.Get(&faceVertexCounts, UsdTimeCode::Default()) || faceVertexCounts.empty())
    {
        delete[] meshDesc.vertices;
        meshDesc.vertices = nullptr;
        delete[] meshDesc.indices;
        meshDesc.indices = nullptr;
        return false;
    }
    else
    {
        meshDesc.numFaces = (int)faceVertexCounts.size();
        auto faceSizes = new int[meshDesc.numFaces];

        for (int i = 0; i < meshDesc.numFaces; i++)
        {
            faceSizes[i] = faceVertexCounts[i];
        }

        meshDesc.faceSizes = faceSizes;
    }

    // set the global transform

    GfMatrix4d usdTransform = xformCache.GetLocalToWorldTransform(prim);

    AffineTransformD transform(Mat33d(usdTransform[0][0],
                                      usdTransform[1][0],
                                      usdTransform[2][0],
                                      usdTransform[0][1],
                                      usdTransform[1][1],
                                      usdTransform[2][1],
                                      usdTransform[0][2],
                                      usdTransform[1][2],
                                      usdTransform[2][2]),
                               Vec3d(usdTransform[3][0], usdTransform[3][1], usdTransform[3][2]));

    meshDesc.transform = transform;
    meshDesc.groupId = 0; // all meshes in same group for now

    if (meshDesc.numVertices == 0 || meshDesc.numIndices == 0 || meshDesc.numFaces == 0)
    {
        delete[] meshDesc.vertices;
        meshDesc.vertices = nullptr;
        delete[] meshDesc.indices;
        meshDesc.indices = nullptr;
        delete[] meshDesc.faceSizes;
        meshDesc.faceSizes = nullptr;

        return false;
    }

    return true;
}


void GetStageMeshDescriptors(std::vector<ClashMeshDescriptor>& meshDescriptors,
                             SdfPathVector& paths,
                             const UsdStageRefPtr& usdStage,
                             const std::vector<UsdPrim>& prims)
{
    UsdGeomXformCache xformCache(0.0);

    if (prims.empty())
    {
        for (const auto& prim : usdStage->Traverse())
        {
            ClashMeshDescriptor meshDesc;
            if (_GetMeshDescriptor(meshDesc, prim, xformCache))
            {
                meshDescriptors.push_back(meshDesc);
                paths.push_back(prim.GetPath());
            }
        }
    }
    else
    {
        for (const auto& prim : prims)
        {
            ClashMeshDescriptor meshDesc;
            if (_GetMeshDescriptor(meshDesc, prim, xformCache))
            {
                meshDescriptors.push_back(meshDesc);
                paths.push_back(prim.GetPath());
            }
        }
    }
}


} // namespace usd_optimize
