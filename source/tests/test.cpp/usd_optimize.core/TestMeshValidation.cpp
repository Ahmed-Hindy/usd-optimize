// SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
// SPDX-License-Identifier: Apache-2.0
//

// Usd Optimize Core
#include <usd_optimize/core/geometry/MeshValidation.h>

// USD
#include <pxr/base/gf/vec3f.h>
#include <pxr/base/vt/array.h>

// doctest
#include <doctest/doctest.h>

// Standard library
#include <cmath>
#include <limits>
#include <string>


using namespace usd_optimize;
PXR_NAMESPACE_USING_DIRECTIVE


TEST_CASE("validateMeshTopology")
{
    // A single well-formed triangle.
    const VtVec3fArray points{ GfVec3f(0, 0, 0), GfVec3f(1, 0, 0), GfVec3f(0, 1, 0) };
    const VtIntArray counts{ 3 };
    const VtIntArray indices{ 0, 1, 2 };

    SUBCASE("valid triangle passes")
    {
        std::string reason = "unset";
        CHECK(validateMeshTopology(points, counts, indices, &reason));
        CHECK(reason == "unset"); // reason is only written on failure
    }

    SUBCASE("empty topology is trivially valid")
    {
        CHECK(validateMeshTopology(points, VtIntArray{}, VtIntArray{}, nullptr));
    }

    SUBCASE("index out of range fails (bad_index repro)")
    {
        std::string reason;
        // index 5 references a point that does not exist (only 3 points).
        CHECK_FALSE(validateMeshTopology(points, VtIntArray{ 3 }, VtIntArray{ 0, 1, 5 }, &reason));
        CHECK(!reason.empty());
    }

    SUBCASE("negative index fails")
    {
        CHECK_FALSE(validateMeshTopology(points, VtIntArray{ 3 }, VtIntArray{ 0, -1, 2 }, nullptr));
    }

    SUBCASE("count/index mismatch fails (count_mismatch repro)")
    {
        // sum(counts) = 4 but only 3 indices provided (too few indices).
        CHECK_FALSE(validateMeshTopology(points, VtIntArray{ 4 }, VtIntArray{ 0, 1, 2 }, nullptr));
        // sum(counts) = 6 but only 3 indices provided (too few indices).
        CHECK_FALSE(validateMeshTopology(points, VtIntArray{ 3, 3 }, VtIntArray{ 0, 1, 2 }, nullptr));
        // sum(counts) = 2 but 3 indices provided (extra trailing index) -- the other direction.
        CHECK_FALSE(validateMeshTopology(points, VtIntArray{ 2 }, VtIntArray{ 0, 1, 2 }, nullptr));
    }

    SUBCASE("negative face vertex count fails")
    {
        CHECK_FALSE(validateMeshTopology(points, VtIntArray{ -3 }, VtIntArray{ 0, 1, 2 }, nullptr));
    }

    SUBCASE("non-finite point fails")
    {
        VtVec3fArray badPoints = points;
        badPoints[1] = GfVec3f(std::numeric_limits<float>::quiet_NaN(), 0, 0);
        CHECK_FALSE(validateMeshTopology(badPoints, counts, indices, nullptr));

        badPoints[1] = GfVec3f(std::numeric_limits<float>::infinity(), 0, 0);
        CHECK_FALSE(validateMeshTopology(badPoints, counts, indices, nullptr));
    }
}
