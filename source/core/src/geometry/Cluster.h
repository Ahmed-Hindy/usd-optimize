// SPDX-FileCopyrightText: Copyright (c) 2020-2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
// SPDX-License-Identifier: Apache-2.0
//

#pragma once

// Usd Optimize Core
#include "usd_optimize/core/Defs.h"
#include "usd_optimize/core/UsdIncludes.h"

// USD
#include <pxr/base/gf/bbox3d.h>
#include <pxr/base/gf/matrix4d.h>
#include <pxr/base/vt/array.h>


namespace usd_optimize
{

constexpr const int INVALID_CLUSTER = -1;

enum class ClusterMode
{
    eNone = 0, // No spatial clustering
    eBoundingBox = 1, // Cluster to a maximum bounding box size
    eVertexCount = 2, // Cluster based on a maximum vertex count
    eCoincidentBoundary = 3, // Cluster meshes that share a coincident boundary edge (a shared seam)
};

/// Helper struct
/// In order to build a BVH you must populate a vector of these structs
/// that have the bound/centroid populated.
struct MeshNode
{

    explicit MeshNode()
    {
    }

    PXR_NS::GfBBox3d bound;
    PXR_NS::GfVec3d centroid;

    size_t nvertex = 0;
    size_t originalIndex = -1;
};


using MeshNodePtr = std::shared_ptr<MeshNode>;


struct BVHNode
{
    BVHNode(const MeshNode* mesh, const PXR_NS::GfBBox3d& bounds);

    const MeshNode* mesh = nullptr;
    PXR_NS::GfBBox3d bounds;
    PXR_NS::GfRange3d range;
    size_t nvertex = 0;
    std::unique_ptr<BVHNode> left = nullptr;
    std::unique_ptr<BVHNode> right = nullptr;

    bool isLeaf() const
    {
        return mesh != nullptr;
    }
};


/// Simple BVH implementation.
/// Allows efficient querying of intersecting bounds.
class BVH
{

public:
    /// Constructor
    ///
    /// Builds a BVH based on \p meshes. The shared pointers in \p meshes are expected
    /// to be valid until no more use of the BVH is required, it uses raw pointers
    /// to refer to them internally.
    ///
    /// \param meshes Input meshes to build a BVH from
    explicit BVH(const std::vector<MeshNodePtr>& meshes);

    /// Query the BVH for any intersecting meshes using the specified threshold.
    ///
    /// Given the MeshNode \p target, find any neighboring MeshNodes that are less than
    /// \p maxDistance away from it in any direction.
    ///
    /// \param target The target MeshNode to find neighbors for
    /// \param maxDistance The maximum distance
    /// \param neighbors Output vector to append the neighbors to
    void findNeighbors(const MeshNode* target, double maxDistance, std::vector<const MeshNode*>& neighbors) const;

    /// Return the root node.
    ///
    /// Returns a raw pointer to the root node so that you can iterate the BVH.
    ///
    /// \return Root node
    BVHNode* getRoot() const;

private:
    /// Construct a BVH node
    ///
    /// Recursively builds BVH nodes using the meshes within the range \p start to \p end.
    /// The members inside \p meshes will be sorted when this function is called, but only
    /// the ones within the specified range.
    ///
    /// If there is only one mesh (i.e. \p start == \p end) a leaf node will be created. If
    /// there are multiple meshes then a node with left/right child nodes will be returned.
    std::unique_ptr<BVHNode> buildBVH(std::vector<const MeshNode*>& meshes, size_t start, size_t end);

    /// Recursive function used internally as part of querying for neighbors.
    void findNeighborsRecursive(const BVHNode* node,
                                const MeshNode* target,
                                const PXR_NS::GfRange3d& targetRange,
                                std::vector<const MeshNode*>& neighbors) const;

    /// Members
    std::unique_ptr<BVHNode> m_root;
};

/// Spatially cluster the specified mesh nodes.
///
/// \p clusters should be resized to the size of \p nodes and initialized with \a INVALID_CLUSTER before
/// calling this function.
///
/// Upon completion the indexing of \p clusters will match \p nodes and be populated with the
/// cluster id for each MeshNodePtr. This number is arbitrary; the only thing that matters is
/// that clustered meshes will have the same id.
///
/// If \p mode is ClusterMode::eBoundingBox then the argument \p maxSize is the maximum size in bounds
/// that an output cluster can be. If it is ClusterMode::eVertexCount then it controls the maximum
/// number of vertices that can be clustered together.
///
/// \param mode The mode to cluster by
/// \param nodes The nodes to cluster
/// \param epsilon The max distance/threshold
/// \param maxSize The maximum size or vertex count of a mesh cluster
/// \param clusters Output vector of unique cluster IDs
void spatiallyClusterMeshes(ClusterMode mode,
                            const std::vector<MeshNodePtr>& nodes,
                            double epsilon,
                            double maxSize,
                            std::vector<int>& clusters);


/// Geometry of a single mesh used as input to \ref clusterByCoincidentBoundary.
///
/// The arrays are referenced (not copied) and must outlive the clustering call. Points are in the mesh's local space;
/// \a localToWorld is used to bring boundary vertices into a common (world) space so that meshes authored under
/// different transforms can be compared.
struct BoundaryMeshData
{
    const PXR_NS::VtVec3fArray* points = nullptr;
    const PXR_NS::VtIntArray* faceVertexCounts = nullptr;
    const PXR_NS::VtIntArray* faceVertexIndices = nullptr;
    PXR_NS::GfMatrix4d localToWorld = PXR_NS::GfMatrix4d(1.0);
};


/// Cluster meshes that share coincident boundary vertices (i.e. a shared "seam").
///
/// A boundary vertex is a vertex that lies on a boundary edge - an edge used by exactly one face. Two meshes are
/// considered connected when they share at least \p minSharedVertices boundary vertices that coincide in world space
/// (each pair of positions within \p tolerance). Requiring more than one shared vertex avoids merging meshes that
/// merely touch at a single corner point, while still catching seams whose tessellation differs on each side (so the
/// boundary vertices coincide even though the boundary edges do not align).
///
/// Connectivity is transitive: meshes are grouped into connected components, so a chain A-B-C is placed in one cluster
/// even if A and C do not share vertices directly.
///
/// \p clusters must be sized to \p meshes and initialized with \a INVALID_CLUSTER before calling. On return each entry
/// holds the cluster id for the corresponding mesh, or remains \a INVALID_CLUSTER if the mesh shares no seam with any
/// other mesh (such meshes are intentionally left unmerged, mirroring the other spatial modes).
///
/// \param meshes The geometry of the meshes to cluster
/// \param tolerance The maximum distance between boundary vertices for them to be considered coincident
/// \param minSharedVertices The minimum number of coincident boundary vertices two meshes must share to be connected
///                          (clamped to a minimum of 1)
/// \param clusters Output vector of unique cluster ids
USD_OPTIMIZE_EXPORT
void clusterByCoincidentBoundary(const std::vector<BoundaryMeshData>& meshes,
                                 double tolerance,
                                 int minSharedVertices,
                                 std::vector<int>& clusters);


} // namespace usd_optimize
