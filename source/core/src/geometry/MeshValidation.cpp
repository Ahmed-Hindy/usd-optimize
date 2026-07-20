// SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
// SPDX-License-Identifier: Apache-2.0
//

#include "usd_optimize/core/geometry/MeshValidation.h"

// C++
#include <cmath>
#include <cstdint>

PXR_NAMESPACE_USING_DIRECTIVE


namespace usd_optimize
{

bool validateMeshTopology(const VtVec3fArray& points,
                          const VtIntArray& faceVertexCounts,
                          const VtIntArray& faceVertexIndices,
                          std::string* reason)
{
    const auto setReason = [&](std::string message)
    {
        if (reason != nullptr)
        {
            *reason = std::move(message);
        }
    };

    const int64_t numPoints = static_cast<int64_t>(points.size());
    const int64_t numIndices = static_cast<int64_t>(faceVertexIndices.size());

    // sum(faceVertexCounts) must exactly cover faceVertexIndices; a mismatch (or a negative count)
    // makes the per-face rolling offset walk off the end of faceVertexIndices.
    int64_t countSum = 0;
    for (int count : faceVertexCounts)
    {
        if (count < 0)
        {
            setReason("negative faceVertexCount");
            return false;
        }
        countSum += count;
    }

    if (countSum != numIndices)
    {
        setReason("sum(faceVertexCounts)=" + std::to_string(countSum) +
                  " != len(faceVertexIndices)=" + std::to_string(numIndices));
        return false;
    }

    // Every face vertex index must address a real point.
    for (int index : faceVertexIndices)
    {
        if (index < 0 || index >= numPoints)
        {
            setReason("faceVertexIndex " + std::to_string(index) + " out of range [0, " + std::to_string(numPoints) + ")");
            return false;
        }
    }

    // Non-finite coordinates (NaN/Inf) break downstream geometry math (extents, projections).
    for (const GfVec3f& p : points)
    {
        if (!std::isfinite(p[0]) || !std::isfinite(p[1]) || !std::isfinite(p[2]))
        {
            setReason("non-finite point coordinate");
            return false;
        }
    }

    return true;
}

} // namespace usd_optimize
