// SPDX-FileCopyrightText: Copyright (c) 2020-2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
// SPDX-License-Identifier: Apache-2.0
//

#pragma once

// Usd Optimize Core
#include <usd_optimize/core/Defs.h>
#include <usd_optimize/core/Operation.h>
#include <usd_optimize/core/UsdIncludes.h>
#include <usd_optimize/core/geometry/DeduplicateUtils.h>


namespace usd_optimize
{


// Methods available for conforming duplicate meshes
enum class DuplicateOption
{
    eCopyValues = 0, // Copy the points and normals values (and all array attributes and primvars in fuzzy mode)
    eReference = 1, // Reference composition arc
    eInstanceableReference = 2, // Reference composition arc with instanceable true
    eSetAttribute = 3, // Set duplication set attribute
    ePointInstancer = 4, // Replace duplicate meshes with a UsdGeomPointInstancer per duplicate set
};


/// Identify identical mesh prims in the stage and ensure they are seen as duplicates.
class DeduplicateGeometryOperation : public Operation
{

    // Where to author PointInstancers
    enum class PointInstancerLocation
    {
        eCommonRoot = 0, // Use the deepest common ancestor of the duplicate meshes as the parent
        eCustomPath = 1, // Use a user-supplied parent path (created as an Xform if missing)
    };

public:
    /// Constructor
    explicit DeduplicateGeometryOperation();

    /// Destructor
    ~DeduplicateGeometryOperation() override;

    /// Get the author of this plugin
    std::string getAuthor() const override;

    /// Get the version of this plugin
    UsdOptimizePluginVersion getVersion() const override;

    /// Get the category for reporting.
    std::string getCategory() const override;

    /// Get the display group.
    std::string getDisplayGroup() const override;

    /// Support Analysis
    bool getSupportsAnalysis() const override;

protected:
    /// Entry-point for execution
    OperationResult executeImpl() override;

    /// Entry-point for analysis
    OperationResult executeAnalysisImpl() override;

private:
    void _conformUsingComposition(const PrimVectors& equalMeshVectors);
    void _conformTopologyAttributeValues(const PrimVector& prims);
    void _createPointInstancers(const PrimVectors& equalMeshVectors);
    PrimVectors _findIdenticalMeshes(const PrimVectors& equalMeshVectors);
    void _copyPrimData(const PXR_NS::UsdPrim& source, const PXR_NS::UsdPrim& target);

    /// Compute duplicate geometry
    ///
    /// Resolves the prims to process based on operation arguments, and then computes vectors
    /// of prims that are duplicates.
    ///
    /// \param resolvedPrims Output parameter that will contain all prims that were checked
    /// \param primVectors Output parameter containing duplicate results
    void computeEqualGeometrySets(std::vector<PXR_NS::UsdPrim>& resolvedPrims, PrimVectors& primVectors);

    std::vector<std::string> m_paths;
    DuplicateOption m_duplicateMethod = DuplicateOption::eInstanceableReference;
    bool m_considerDeepTransforms = true;
    float m_tolerance = 0.001f;
    bool m_fuzzy = false;
    bool m_useGpu = false;
    bool m_allowScaling = false;
    bool m_fuzzyOnly = false;
    std::vector<std::string> m_ignoreAttributes;
    PointInstancerLocation m_pointInstancerLocation = PointInstancerLocation::eCommonRoot;
    std::string m_pointInstancerParentPath;
    int m_minimumDuplicates = 2;
};


} // namespace usd_optimize
