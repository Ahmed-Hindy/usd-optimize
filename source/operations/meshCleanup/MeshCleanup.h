// SPDX-FileCopyrightText: Copyright (c) 2020-2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
// SPDX-License-Identifier: Apache-2.0
//

#pragma once

// Usd Optimize Core
#include <usd_optimize/core/OmniOperation.h>

// C++
#include <atomic>

// TBB
#include <tbb/concurrent_vector.h>


namespace usd_optimize
{

/// Merge vertices using OmniMesh.
class MeshCleanupOperation : public OmniOperation
{
public:
    MeshCleanupOperation();

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
    ProcessedData* processMesh(const PXR_NS::UsdPrim& prim, tbb::task_group_context&);

    /// Log a summary of the cleanup result (vertices/faces removed).
    void executePost(const TotalStats& totalStats) override;

    /// Entry-point for analysis
    OperationResult executeAnalysisImpl() override;

    /// Analyze the stage
    OperationResult recordAnalysis();

private:
    /// Used for analysis mode
    struct Report
    {
        Report()
        {
            clear();
        }

        void clear()
        {
            meshesThatAreNonManifolds = 0;
            meshesWithMergeableVertices = 0;
            meshesWithDegenerateEdges = 0;
            meshesWithDegenerateFaces = 0;
            meshesWithIsolatedVertices = 0;
            meshesWithDuplicateFaces = 0;
        }

        std::atomic<size_t> meshesThatAreNonManifolds;
        std::atomic<size_t> meshesWithMergeableVertices;
        std::atomic<size_t> meshesWithDegenerateEdges;
        std::atomic<size_t> meshesWithDegenerateFaces;
        std::atomic<size_t> meshesWithIsolatedVertices;
        std::atomic<size_t> meshesWithDuplicateFaces;
        tbb::concurrent_vector<PXR_NS::UsdPrim> meshesWithInconsistentWindings;
    };

    bool m_mergeVertices;
    float m_tolerance;
    bool m_makeManifold;
    bool m_removeIsolatedVertices;
    bool m_mergeBoundaries;
    bool m_mergeNeighbors;
    bool m_contractDegenerateEdges;
    bool m_removeDegenerateFaces;
    bool m_removeDuplicateFaces;
    bool m_coorientFaces;

    Report m_report;
};

} // namespace usd_optimize
