// SPDX-FileCopyrightText: Copyright (c) 2020-2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
// SPDX-License-Identifier: Apache-2.0
//

#pragma once

// Usd Optimize Core
#include <usd_optimize/core/Defs.h>
#include <usd_optimize/core/Operation.h>
#include <usd_optimize/core/UsdIncludes.h>


namespace usd_optimize
{


/// Utility Function
enum class UtilityFunctionType
{
    eDeinstance = 0, // Deinstance prims
    eUnbindMaterials = 2, // Unbind materials
    eSetInstanceable = 3, // Set instanceable
    eFlattenInstance = 4, // Flatten instance
};


/// Utility Function Operation
///
/// A collection of small helper functions, such as deinstancing a scene, that don't necessarily need a
/// full blown operation of their own.
///
/// The operation only supports running one function at a time. While they are all simple, the idea is
/// that you can add more to control the order better, rather than trying to run multiple things in
/// one go.
class UtilityFunctionOperation : public Operation
{

public:
    /// Constructor
    explicit UtilityFunctionOperation();

    /// Get the author of this plugin
    std::string getAuthor() const override;

    /// Get the version of this plugin
    UsdOptimizePluginVersion getVersion() const override;

    /// Get the category for reporting.
    std::string getCategory() const override;

protected:
    /// Entry point
    OperationResult executeImpl() override;

private:
    /// Deinstance any prims with instanceable=True
    bool deinstance(const std::vector<PXR_NS::UsdPrim>& prims);

    /// Unbind materials
    bool unbindMaterials(const std::vector<PXR_NS::UsdPrim>& prims);

    /// Check a referenced prim to see if it can be made instanceable
    bool makePrimInstanceable(const PXR_NS::UsdPrim& prim);

    /// Set instanceable
    bool setInstanceable(const std::vector<PXR_NS::UsdPrim>& prims);

    /// Disable instancing and "flatten" an instance, removing composition ARCs.
    bool flattenInstances(const std::vector<PXR_NS::UsdPrim>& prims);

    std::vector<std::string> m_paths;
    UtilityFunctionType m_functionType = UtilityFunctionType::eDeinstance;
};


} // namespace usd_optimize
