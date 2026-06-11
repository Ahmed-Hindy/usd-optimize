// SPDX-FileCopyrightText: Copyright (c) 2020-2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
// SPDX-License-Identifier: Apache-2.0
//

#include "usd_optimize/core/geometry/Cluster.h"

// Usd Optimize Core
#include "usd_optimize/core/geometry/DisjointSet.h"

// USD
#include <pxr/base/tf/hash.h>

// C++
#include <algorithm>
#include <cmath>
#include <map>
#include <unordered_map>
#include <unordered_set>
#include <utility>

PXR_NAMESPACE_USING_DIRECTIVE


namespace usd_optimize
{

/// Hashes a std::pair using the standard TfHash combiner, so std::pair can be used as an unordered_map key.
struct PairHash
{
    template <typename A, typename B>
    size_t operator()(const std::pair<A, B>& value) const
    {
        return PXR_NS::TfHash::Combine(value.first, value.second);
    }
};

/// Assigns a single canonical id to boundary-vertex positions that are coincident within a tolerance.
///
/// Positions are bucketed into a uniform grid with cell size equal to the tolerance. When canonicalizing a position the
/// 27 neighboring cells are searched for an existing representative within the tolerance, so points that straddle a
/// cell boundary still resolve to the same id.
class CoincidentVertexMap
{
public:
    explicit CoincidentVertexMap(const double tolerance)
        : m_tolerance(tolerance)
        , m_invCellSize(1.0 / tolerance)
    {
    }

    int canonicalId(const GfVec3d& p)
    {
        const int64_t cx = cellCoord(p[0]);
        const int64_t cy = cellCoord(p[1]);
        const int64_t cz = cellCoord(p[2]);

        const double toleranceSq = m_tolerance * m_tolerance;

        // Search the cell and its 26 neighbors for an existing representative within tolerance.
        for (int64_t dz = -1; dz <= 1; ++dz)
        {
            for (int64_t dy = -1; dy <= 1; ++dy)
            {
                for (int64_t dx = -1; dx <= 1; ++dx)
                {
                    auto it = m_cells.find(cellKey(cx + dx, cy + dy, cz + dz));
                    if (it == m_cells.end())
                    {
                        continue;
                    }
                    for (const int id : it->second)
                    {
                        if ((m_positions[id] - p).GetLengthSq() <= toleranceSq)
                        {
                            return id;
                        }
                    }
                }
            }
        }

        // No coincident representative found - create a new canonical id.
        const int id = static_cast<int>(m_positions.size());
        m_positions.push_back(p);
        m_cells[cellKey(cx, cy, cz)].push_back(id);
        return id;
    }

private:
    int64_t cellCoord(double v) const
    {
        return static_cast<int64_t>(std::floor(v * m_invCellSize));
    }

    static size_t cellKey(int64_t x, int64_t y, int64_t z)
    {
        // Combine the cell coordinates into a single key. Collisions only grow a candidate list which is still
        // distance-checked, so they never affect correctness.
        return PXR_NS::TfHash::Combine(x, y, z);
    }

    double m_tolerance;
    double m_invCellSize;
    std::vector<GfVec3d> m_positions;
    std::unordered_map<size_t, std::vector<int>> m_cells;
};


BVHNode::BVHNode(const MeshNode* mesh, const PXR_NS::GfBBox3d& bounds)
    : mesh(mesh)
    , bounds(bounds)
    , range(bounds.ComputeAlignedRange())
{
    if (mesh)
    {
        nvertex = mesh->nvertex;
    }
}


BVH::BVH(const std::vector<MeshNodePtr>& meshes)
{
    // We want to be able to pass a vector internally and sort parts of it, without affecting
    // the original, so we make a copy. At this point we also use the raw pointers rather than
    // copying shared pointers more.
    std::vector<const MeshNode*> _meshes(meshes.size());

    // Record the original index. As we will sort chunks of this copy, we'll need to know how to
    // get back to the original. We do that on the original MeshNode, then copy, so we can maintain
    // const pointers elsewhere.
    for (size_t index = 0; index < _meshes.size(); ++index)
    {
        meshes[index]->originalIndex = index;
        _meshes[index] = meshes[index].get();
    }

    // Do the actual construction of the tree
    m_root = buildBVH(_meshes, 0, _meshes.size() - 1);
}


void BVH::findNeighbors(const MeshNode* target, double maxDistance, std::vector<const MeshNode*>& neighbors) const
{
    // Get the original target bounding box range
    GfRange3d range = target->bound.ComputeAlignedRange();

    // Expand it by the specified threshold in each direction
    // Anything leaf that intersects with this will be considered a neighbor
    range.SetMin(range.GetMin() - GfVec3d(maxDistance, maxDistance, maxDistance));
    range.SetMax(range.GetMax() + GfVec3d(maxDistance, maxDistance, maxDistance));

    // Now we have the target range, begin the actual query
    findNeighborsRecursive(m_root.get(), target, range, neighbors);
}


static GfBBox3d calculateBounds(const std::vector<const MeshNode*>& meshes, size_t start, size_t end)
{
    // Calculate the cumulative bounds of all child meshes
    GfBBox3d result = meshes[start]->bound;
    for (size_t i = start + 1; i <= end; ++i)
    {
        result = GfBBox3d::Combine(result, meshes[i]->bound);
    }

    return result;
}


static int chooseSplitAxis(const GfBBox3d& bounds)
{

    const auto& matrix = bounds.GetMatrix();
    GfVec3d min = matrix.Transform(bounds.GetRange().GetCorner(0));
    GfVec3d max = matrix.Transform(bounds.GetRange().GetCorner(7));

    // Calculate dimensions
    double width = max[0] - min[0];
    double height = max[1] - min[1];
    double depth = max[2] - min[2];

    // Choose the axis with the maximum dimension
    if (width >= height && width >= depth)
    {
        return 0; // X
    }
    else if (height >= width && height >= depth)
    {
        return 1; // Y
    }
    else
    {
        return 2; // Z
    }
}


std::unique_ptr<BVHNode> BVH::buildBVH(std::vector<const MeshNode*>& meshes, size_t start, size_t end)
{

    // If start is end then create a leaf node
    if (start == end)
    {
        return std::make_unique<BVHNode>(meshes[start], meshes[start]->bound);
    }

    // Calculate the overall bounds for the current node, which encompasses all of its children
    GfBBox3d bounds = calculateBounds(meshes, start, end);

    // Choose the axis along which to split the bounding boxes then sort this segment of meshes on it
    int splitAxis = chooseSplitAxis(bounds);

    std::sort(meshes.begin() + start,
              meshes.begin() + end + 1,
              [&](const MeshNode* a, const MeshNode* b) { return a->centroid[splitAxis] < b->centroid[splitAxis]; });

    // Calculate the split index
    size_t splitIndex = start + (end - start) / 2;

    // Create the new branch node
    auto node = std::make_unique<BVHNode>(nullptr, bounds);

    // Recursively build the left and right child nodes and assign to the new branch
    node->left = buildBVH(meshes, start, splitIndex);
    node->right = buildBVH(meshes, splitIndex + 1, end);

    // Update total vertex count
    node->nvertex = node->left->nvertex + node->right->nvertex;

    return node;
}


void BVH::findNeighborsRecursive(const BVHNode* node,
                                 const MeshNode* target,
                                 const GfRange3d& targetRange,
                                 std::vector<const MeshNode*>& neighbors) const
{

    // Test if this node intersects the target range.
    // If not, we can ignore this branch.
    GfRange3d intersection = GfRange3d::GetIntersection(node->range, targetRange);
    if (intersection.IsEmpty())
    {
        return;
    }

    // If this is a leaf node then it intersects with the target range, and is therefore
    // a neighbor.
    if (node->isLeaf())
    {
        // Don't add itself as a neighbor
        if (node->mesh != target)
        {
            neighbors.emplace_back(node->mesh);
        }
    }
    else
    {
        // Carry on and check both branches
        findNeighborsRecursive(node->left.get(), target, targetRange, neighbors);
        findNeighborsRecursive(node->right.get(), target, targetRange, neighbors);
    }
}


BVHNode* BVH::getRoot() const
{
    return m_root.get();
}


/// Cluster meshes based on a maximum vertex count.
///
/// This function uses the BVH which tracks vertex count. It's a very simple iteration through
/// the tree until a branch is found that has fewer vertices than the specified maximum. As
/// the BVH is already created based on bounds, we can simply find a branch with the appropriate
/// number of vertices and cluster any leaf nodes underneath it, knowing that they will be spatially
/// similar.
///
/// This is a recursive function. At the point the \p node vertex count is less than or equal
/// to \p maxSize, \p stamp will be set to true and \p clusterId will be incremented. All leaf
/// nodes found underneath \p node will then be "stamped" with the current cluster id.
///
/// \param node The current node to process
/// \param maxSize The maximum number of vertices to cluster
/// \param clusterId Unique cluster ID
/// \param clusters The output clusters, one per mesh
/// \param stamp Whether we are within a cluster
static void clusterByVertexCount(BVHNode* node, size_t maxSize, int& clusterId, std::vector<int>& clusters, bool stamp)
{
    // If stamp is false (have not yet found a small enough section) then check the vertex count.
    if (!stamp && node->nvertex <= maxSize)
    {
        // stamp was off, so this means we have just encountered a branch of the BVH that
        // is within the target vertex count. Bump the cluster id as this is now a cluster
        // and enable stamp for this branch.
        ++clusterId;
        stamp = true;
    }

    if (node->isLeaf())
    {
        // If stamp is on we want to apply this cluster ID to every leaf mesh we find.
        if (stamp)
        {
            clusters[node->mesh->originalIndex] = clusterId;
        }
    }
    else
    {
        // Not a leaf so recurse both ways
        clusterByVertexCount(node->left.get(), maxSize, clusterId, clusters, stamp);
        clusterByVertexCount(node->right.get(), maxSize, clusterId, clusters, stamp);
    }
}


void spatiallyClusterMeshes(ClusterMode mode,
                            const std::vector<MeshNodePtr>& nodes,
                            double epsilon,
                            double maxSize,
                            std::vector<int>& clusters)
{
    // Build the BVH
    BVH bvh(nodes);

    // Next cluster counter
    int clusterId = INVALID_CLUSTER;

    if (mode == ClusterMode::eVertexCount)
    {
        clusterByVertexCount(bvh.getRoot(), (size_t)maxSize, clusterId, clusters, false);
        return;
    }

    // perform a first pass to find all the neighbors for each mesh.
    // note: This is faster to do ahead of time since we need to do this only once for each mesh. It also avoids going
    //       into a death spiral with large spatial thresholds where each mesh is stacking recursions into the BVH to
    //       find neighbors.
    // WARNING: for some unknown reason this for loop CANNOT be parallelized on Windows, it incurs massive performance
    //          overhead. We could investigate this further, but for now I don't think the performance cost is worth it.
    std::vector<std::vector<const MeshNode*>> allNeighbors(nodes.size());
    for (size_t i = 0; i < nodes.size(); ++i)
    {
        const MeshNodePtr& mesh = nodes[i];
        std::vector<const MeshNode*>& neighbors = allNeighbors.at(i);
        bvh.findNeighbors(mesh.get(), epsilon, neighbors);
    }

    // Performance optimization: instead of a standard queue we use a vector of vectors that
    // tracks the descending index we're currently processing in each section. This preserves the
    // original clustering behaviour while avoiding data movement — we just walk a pointer over
    // the pre-computed nearest neighbors.
    std::vector<std::pair<std::vector<const MeshNode*>*, int>> neighborsQueue;
    neighborsQueue.reserve(nodes.size());

    // iterate through each mesh and cluster them - not worth multi-threading this code since we'd need a mutex around
    // assigning clusters which would be slower than just doing it in a single thread.
    for (size_t i = 0; i < nodes.size(); ++i)
    {
        // If this mesh was already assigned a cluster, skip it.
        if (clusters[i] != INVALID_CLUSTER)
        {
            continue;
        }

        std::vector<const MeshNode*>& neighbors = allNeighbors[i];
        if (neighbors.empty())
        {
            continue;
        }

        const MeshNodePtr& mesh = nodes[i];

        // initialise the queue with the neighbors of this mesh
        neighborsQueue.clear();
        int queueIndex = 0;
        neighborsQueue.emplace_back(&neighbors, static_cast<int>(neighbors.size()) - 1);

        // We might be able to cluster this mesh, but need to find out if any of the neighbors are
        // valid to include.
        int _clusterId = INVALID_CLUSTER;

        // Track the bounds for this cluster
        GfBBox3d currentBound = mesh->bound;

        // Process the neighbors. For each neighbor, check if it has already been clustered. If not,
        // check whether merging it would exceed the max size. If not, include it in this cluster and
        // then carry on checking its neighbors until we hit the max size.
        while (queueIndex >= 0)
        {
            auto& subQueue = neighborsQueue[static_cast<size_t>(queueIndex)];
            // sub queue complete? move to the next
            if (subQueue.second < 0)
            {
                neighborsQueue.pop_back();
                --queueIndex;
                continue;
            }

            while (subQueue.second >= 0)
            {
                const MeshNode* neighbor = (*subQueue.first)[static_cast<size_t>(subQueue.second)];
                --subQueue.second;

                // Skip if this neighbor is already part of a cluster.
                size_t originalIndex = neighbor->originalIndex;
                if (clusters[originalIndex] != INVALID_CLUSTER)
                {
                    continue;
                }

                // Combine the current cluster bound with the new bound, so we can check whether
                // it would exceed the max size
                GfBBox3d newBound = GfBBox3d::Combine(currentBound, neighbor->bound);
                GfRange3d range = newBound.ComputeAlignedRange();
                GfVec3d size = range.GetSize();

                // Currently checking the individual dimensions. This is to get a grid/box like
                // bound, rather than using Length(Sq).
                if (size[0] > maxSize || size[1] > maxSize || size[2] > maxSize)
                {
                    continue;
                }

                // Cool, we found something that is valid to cluster. Now we can make sure we have a
                // new cluster id and assign it to the original mesh, along with this one.
                if (_clusterId == INVALID_CLUSTER)
                {
                    _clusterId = ++clusterId;
                    clusters[i] = _clusterId;
                }

                // Update current total bound and assign clusterId to neighbor
                currentBound = newBound;
                clusters[originalIndex] = clusterId;

                std::vector<const MeshNode*>& nextNeighbors = allNeighbors[originalIndex];
                if (!nextNeighbors.empty())
                {
                    neighborsQueue.push_back(std::make_pair(&nextNeighbors, static_cast<int>(nextNeighbors.size()) - 1));
                    queueIndex = static_cast<int>(neighborsQueue.size() - 1);
                    break;
                }
            }
        }
    }
}


void clusterByCoincidentBoundary(const std::vector<BoundaryMeshData>& meshes,
                                 double tolerance,
                                 int minSharedVertices,
                                 std::vector<int>& clusters)
{
    // A non-positive tolerance is meaningless for coincidence testing (and would divide by zero in the grid), so there
    // is nothing to cluster.
    if (tolerance <= 0.0 || meshes.empty())
    {
        return;
    }

    // At least one shared vertex is required to connect two meshes.
    const int minShared = std::max(minSharedVertices, 1);

    CoincidentVertexMap vertexMap(tolerance);

    // For each canonical (coincidence-merged) boundary vertex position, the set of meshes that have a boundary vertex
    // there. Two meshes are candidates for merging where these sets overlap.
    std::unordered_map<int, std::vector<size_t>> vertexToMeshes;

    // Per-mesh scratch reused across meshes to avoid reallocating on every iteration: edge-usage counts (to identify
    // boundary edges used by exactly one face), the local indices lying on a boundary edge, and the canonical world-
    // space ids those resolve to.
    std::unordered_map<std::pair<int, int>, int, PairHash> edgeUse;
    std::unordered_set<int> boundaryVertices;
    std::unordered_set<int> canonicalIds;

    for (size_t meshIndex = 0; meshIndex < meshes.size(); ++meshIndex)
    {
        const BoundaryMeshData& mesh = meshes[meshIndex];
        if (mesh.points == nullptr || mesh.faceVertexCounts == nullptr || mesh.faceVertexIndices == nullptr)
        {
            continue;
        }

        const VtIntArray& faceVertexCounts = *mesh.faceVertexCounts;
        const VtIntArray& faceVertexIndices = *mesh.faceVertexIndices;
        const VtVec3fArray& points = *mesh.points;

        // Count how many faces use each (undirected) edge.
        edgeUse.clear();
        size_t cursor = 0;
        for (int count : faceVertexCounts)
        {
            if (count < 2 || cursor + static_cast<size_t>(count) > faceVertexIndices.size())
            {
                cursor += static_cast<size_t>(std::max(count, 0));
                continue;
            }
            for (int k = 0; k < count; ++k)
            {
                const int a = faceVertexIndices[cursor + k];
                const int b = faceVertexIndices[cursor + (k + 1) % count];
                if (a == b)
                {
                    continue;
                }
                ++edgeUse[std::make_pair(std::min(a, b), std::max(a, b))];
            }
            cursor += static_cast<size_t>(count);
        }

        // Collect the local vertex indices that lie on a boundary edge (an edge used by exactly one face).
        boundaryVertices.clear();
        for (const auto& [edge, uses] : edgeUse)
        {
            if (uses == 1)
            {
                boundaryVertices.insert(edge.first);
                boundaryVertices.insert(edge.second);
            }
        }

        // Resolve each boundary vertex to a canonical world-space id and record this mesh against it. Using a set of
        // canonical ids ensures a mesh is counted at most once per coincident position even if two of its own vertices
        // happen to coincide.
        canonicalIds.clear();
        for (int vertexIndex : boundaryVertices)
        {
            if (vertexIndex < 0 || static_cast<size_t>(vertexIndex) >= points.size())
            {
                continue;
            }
            canonicalIds.insert(vertexMap.canonicalId(mesh.localToWorld.Transform(GfVec3d(points[vertexIndex]))));
        }
        for (int id : canonicalIds)
        {
            vertexToMeshes[id].push_back(meshIndex);
        }
    }

    // Count, for each pair of meshes, how many boundary vertices they share. Two meshes are connected when they share
    // at least minShared coincident boundary vertices.
    std::unordered_map<std::pair<size_t, size_t>, int, PairHash> sharedVertexCount;
    for (const auto& [canonicalId, meshIndices] : vertexToMeshes)
    {
        if (meshIndices.size() < 2)
        {
            continue;
        }
        for (size_t i = 0; i < meshIndices.size(); ++i)
        {
            for (size_t j = i + 1; j < meshIndices.size(); ++j)
            {
                ++sharedVertexCount[std::make_pair(meshIndices[i], meshIndices[j])];
            }
        }
    }

    // Union meshes that share enough boundary vertices. Connectivity is transitive via the disjoint set. The mesh
    // indices [0, meshes.size()) are used directly as the elements of the set.
    std::vector<int> meshIds(meshes.size());
    for (size_t i = 0; i < meshes.size(); ++i)
    {
        meshIds[i] = static_cast<int>(i);
    }

    DisjointSet components(meshIds.data(), meshIds.size());
    for (const auto& [pair, count] : sharedVertexCount)
    {
        if (count >= minShared)
        {
            components.unionSet(static_cast<int>(pair.first), static_cast<int>(pair.second));
        }
    }

    // Assign cluster ids to connected components that contain more than one mesh. Meshes that share no seam remain
    // INVALID_CLUSTER so that they are not merged on their own.
    std::map<int, int> rootMemberCount;
    for (size_t i = 0; i < meshes.size(); ++i)
    {
        ++rootMemberCount[components.findSet(static_cast<int>(i))];
    }

    std::map<int, int> rootClusterId;
    int nextClusterId = INVALID_CLUSTER;
    for (size_t i = 0; i < meshes.size(); ++i)
    {
        const int root = components.findSet(static_cast<int>(i));
        if (rootMemberCount[root] < 2)
        {
            continue;
        }

        auto it = rootClusterId.find(root);
        if (it == rootClusterId.end())
        {
            it = rootClusterId.emplace(root, ++nextClusterId).first;
        }
        clusters[i] = it->second;
    }
}


} // namespace usd_optimize
