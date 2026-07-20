// SPDX-FileCopyrightText: Copyright (c) 2024-2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
// SPDX-License-Identifier: Apache-2.0
//

#pragma once

// Usd Optimize Core
#include <usd_optimize/core/Defs.h>
#include <usd_optimize/core/Operation.h>
#include <usd_optimize/core/UsdIncludes.h>

// std
#include <map>
#include <string>
#include <vector>


namespace usd_optimize
{

using HierarchyMap = std::map<PXR_NS::SdfPath, PXR_NS::SdfPathVector>;

/// Find duplicate prim hierarchies and convert duplicates into internal
/// instanceable references to the first instance (the "prototype").
///
/// This operates at the *hierarchy* level — it operates on whole subtrees,
/// not individual meshes. For per-mesh deduplication see
/// `deduplicateGeometry` (typically chained as a follow-up step).
///
/// Duplicates are identified by a structural hash of each subtree
/// (hierarchy shape, prim type names, sorted authored property names).
/// Each structural group is then partitioned into value-equivalence
/// classes by comparing all authored property values (excluding xformOp
/// values on the root prim, which are expected to differ between
/// instances); every class with two or more members becomes its own
/// prototype. A structurally-identical group containing multiple
/// value-variants therefore yields one prototype per variant, independent
/// of member ordering.
///
/// Creates internal instanceable references from each duplicate subtree to
/// the prototype of its value-equivalence class. The prototype is then
/// traversed in turn, so duplicates nested inside a prototype are themselves
/// consolidated into nested instanceable references — every instance of the
/// prototype inherits that structure, deduplicating shared inner content once.
class DeduplicateHierarchiesOperation : public Operation
{

public:
    /// Constructor
    explicit DeduplicateHierarchiesOperation();

    /// Destructor
    ~DeduplicateHierarchiesOperation() override;

    /// Get the documentation string for this plugin.
    std::string getDocumentation() const override;

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

    /// Entry-point for analysis (find duplicates without mutating stage)
    OperationResult executeAnalysisImpl() override;

private:
    /// Shared logic: find duplicate hierarchies and return the map.
    /// Does NOT mutate the stage.
    HierarchyMap _findDuplicates();
    /// Optional subtree restriction. Empty = walk children of the default prim.
    std::vector<std::string> m_paths;

    /// Tolerance for floating-point property comparison (stage units).
    double m_tolerance = 0.001;

    /// Skip shader output attributes (outputs:*) during value comparison.
    bool m_ignoreShaderOutputs = true;

    /// Maximum number of breadth-first levels to descend (0 = unbounded).
    /// Caps how deep the nested-instance library is built; useful to bound
    /// runtime and avoid over-fragmenting into very deeply nested instances.
    int m_maxDepth = 0;
};


} // namespace usd_optimize
