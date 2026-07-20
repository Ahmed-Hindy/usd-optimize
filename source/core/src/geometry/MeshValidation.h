// SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
// SPDX-License-Identifier: Apache-2.0
//

#pragma once

// Usd Optimize Core
#include "usd_optimize/core/Defs.h"
#include "usd_optimize/core/UsdIncludes.h"

// C++
#include <string>


namespace usd_optimize
{

/// Validate the topology of a polygon mesh before it is indexed.
///
/// Operations that walk faceVertexIndices (splitting, UV projection, etc.) index into the points
/// array and assume the counts and indices are internally consistent. Malformed or adversarial USD
/// can violate that -- an index >= number of points, a negative index, or
/// sum(faceVertexCounts) != len(faceVertexIndices) -- which leads to out-of-bounds heap reads/writes
/// and, in aggregate, heap corruption. Callers must validate up front and skip (or error on) meshes
/// that fail, rather than trusting authored topology.
///
/// Checks performed:
///  - every faceVertexCount is non-negative and sum(faceVertexCounts) == faceVertexIndices.size()
///  - every faceVertexIndex is in the range [0, points.size())
///  - every point coordinate is finite (no NaN/Inf)
///
/// \param points The mesh points.
/// \param faceVertexCounts The per-face vertex counts.
/// \param faceVertexIndices The flattened face vertex indices.
/// \param reason If non-null, set to a short human-readable description when validation fails.
/// \return true if the topology is well-formed, false otherwise.
USD_OPTIMIZE_EXPORT bool validateMeshTopology(const PXR_NS::VtVec3fArray& points,
                                              const PXR_NS::VtIntArray& faceVertexCounts,
                                              const PXR_NS::VtIntArray& faceVertexIndices,
                                              std::string* reason = nullptr);

} // namespace usd_optimize
