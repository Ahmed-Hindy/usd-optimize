// SPDX-FileCopyrightText: Copyright (c) 2024-2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
// SPDX-License-Identifier: Apache-2.0
//
#include "DeduplicateHierarchies.h"

// Usd Optimize Core
#include <usd_optimize/core/Core.h>
#include <usd_optimize/core/JsonUtils.h>
#include <usd_optimize/core/Log.h>
#include <usd_optimize/core/RemovePrims.h>
#include <usd_optimize/core/UsdIncludes.h>
#include <usd_optimize/core/Utils.h>

// USD (extras beyond UsdIncludes.h)
#include <pxr/usd/usd/primRange.h>
#include <pxr/usd/usdGeom/subset.h>

// std
#include <algorithm>
#include <cinttypes>
#include <cstdio>
#include <map>
#include <optional>
#include <set>
#include <string>
#include <unordered_map>
#include <vector>

PXR_NAMESPACE_USING_DIRECTIVE

// Register plugin
USD_OPTIMIZE_PLUGIN_INIT(usd_optimize::DeduplicateHierarchiesOperation);


namespace usd_optimize
{

constexpr const char* s_categoryDedupHierarchies = "DEDUPLICATE_HIERARCHIES";

using PrimVector = std::vector<UsdPrim>;


// Material-related prim filter — mirrors `_is_material_related` in the Python
// processor. Keeps the C++ port in lock-step with the script's traversal so
// the two tiers produce comparable results on the same asset.
static bool _isMaterialRelated(const UsdPrim& prim)
{
    static const std::set<std::string> kMaterialScopes = { "Looks", "Materials" };
    static const std::vector<std::string> kTexturePrefixes = { "Diffuse",   "Specular", "Normal",
                                                               "Roughness", "Metallic", "Emissive",
                                                               "Opacity",   "AO",       "Displacement" };

    if (prim.IsA<UsdShadeMaterial>() || prim.IsA<UsdShadeShader>() || prim.IsA<UsdShadeNodeGraph>() ||
        prim.IsA<UsdGeomSubset>())
    {
        return true;
    }

    const std::string name = prim.GetName().GetString();
    if (kMaterialScopes.count(name) > 0)
    {
        return true;
    }

    for (const auto& prefix : kTexturePrefixes)
    {
        if (name.rfind(prefix, 0) == 0)
        {
            return true;
        }
    }

    return false;
}


// True if the prim authors any references or payloads. Such prims are
// excluded from the duplicate set in internal-reference mode (the script
// does the same — see `_has_references_or_payloads`).
static bool _hasReferencesOrPayloads(const UsdPrim& prim)
{
    return prim.HasAuthoredReferences() || prim.HasAuthoredPayloads();
}


// FNV-1a-64 constants and per-field mixer used by `_structuralHash`.
constexpr uint64_t kFnvOffset = 0xcbf29ce484222325ull;
constexpr uint64_t kFnvPrime = 0x100000001b3ull;

static uint64_t _fnvMix(uint64_t hash, const std::string& s)
{
    for (unsigned char c : s)
    {
        hash ^= c;
        hash *= kFnvPrime;
    }
    // Domain separator between fields: prevents two adjacent fields from
    // colliding with one longer field of the same byte sequence.
    hash ^= 0xff;
    hash *= kFnvPrime;
    return hash;
}


// Structural hash of a subtree. Walks the subtree (depth-first via UsdPrimRange)
// and accumulates an FNV-1a-64 hash over, per descendant:
//   - the descendant's path relative to `root`
//   - the descendant's type name
//   - the descendant's authored property names (sorted, so the hash is
//     order-independent)
//
// Excludes attribute *values* and mesh data by design: pointwise mesh
// equality is `deduplicateGeometry`'s responsibility, and including
// root transforms here would prevent matching duplicates that differ
// only in placement — which is the entire point of instancing.
//
// Returns a 16-character lowercase hex string. Two subtrees produce the
// same string iff their (shape, types, authored property names) match.
static std::string _structuralHash(const UsdPrim& root)
{
    uint64_t hash = kFnvOffset;
    const SdfPath rootPath = root.GetPath();

    for (const UsdPrim& descendant : UsdPrimRange(root))
    {
        const SdfPath relPath = descendant.GetPath().MakeRelativePath(rootPath);
        hash = _fnvMix(hash, relPath.GetAsString());
        hash = _fnvMix(hash, descendant.GetTypeName().GetString());

        std::vector<std::string> propNames;
        for (const TfToken& name : descendant.GetAuthoredPropertyNames())
        {
            propNames.push_back(name.GetString());
        }
        std::sort(propNames.begin(), propNames.end());
        for (const std::string& name : propNames)
        {
            hash = _fnvMix(hash, name);
        }
        // Domain separator between prims.
        hash ^= 0xee;
        hash *= kFnvPrime;
    }

    char buf[17];
    std::snprintf(buf, sizeof(buf), "%016" PRIx64, static_cast<uint64_t>(hash));
    return std::string(buf);
}


// Returns true if a property name is a transform-related attribute that should
// be excluded from value comparison. Instances are expected to differ in
// placement, so xformOp values and xformOpOrder are not meaningful signals.
static bool _isXformProperty(const TfToken& name)
{
    return (UsdGeomXformOp::IsXformOp(name) || name == UsdGeomTokens->xformOpOrder);
}

// The set of value types that `tolerance` applies to: scalar float/double/half,
// GfVec/GfMatrix/GfQuat, and VtArray<T> of each. Centralized as an X-macro so
// `_valuesEqual` (the tolerance comparison) and `_isToleranceFloatType` (the
// fingerprint pre-bucket) can never drift apart. USD only has double-precision
// matrix value types, so there are no float matrices.
#define USD_OPTIMIZE_TOLERANCE_FLOAT_TYPES(X)                                                                          \
    X(float)                                                                                                           \
    X(double)                                                                                                          \
    X(GfHalf)                                                                                                          \
    X(GfVec2f)                                                                                                         \
    X(GfVec2d)                                                                                                         \
    X(GfVec2h)                                                                                                         \
    X(GfVec3f)                                                                                                         \
    X(GfVec3d)                                                                                                         \
    X(GfVec3h)                                                                                                         \
    X(GfVec4f)                                                                                                         \
    X(GfVec4d)                                                                                                         \
    X(GfVec4h)                                                                                                         \
    X(GfMatrix2d)                                                                                                      \
    X(GfMatrix3d)                                                                                                      \
    X(GfMatrix4d)                                                                                                      \
    X(GfQuatf)                                                                                                         \
    X(GfQuatd)                                                                                                         \
    X(GfQuath)                                                                                                         \
    X(VtFloatArray)                                                                                                    \
    X(VtDoubleArray)                                                                                                   \
    X(VtHalfArray)                                                                                                     \
    X(VtVec2fArray)                                                                                                    \
    X(VtVec2dArray)                                                                                                    \
    X(VtVec2hArray)                                                                                                    \
    X(VtVec3fArray)                                                                                                    \
    X(VtVec3dArray)                                                                                                    \
    X(VtVec3hArray)                                                                                                    \
    X(VtVec4fArray)                                                                                                    \
    X(VtVec4dArray)                                                                                                    \
    X(VtVec4hArray)                                                                                                    \
    X(VtMatrix2dArray)                                                                                                 \
    X(VtMatrix3dArray)                                                                                                 \
    X(VtMatrix4dArray)                                                                                                 \
    X(VtQuatfArray)                                                                                                    \
    X(VtQuatdArray)                                                                                                    \
    X(VtQuathArray)

// Compare two VtValues, applying tolerance for floating-point types: scalar
// float/double/half, GfVec/GfMatrix/GfQuat, and VtArray<T> of any of those.
// Integer/topology/string/token/bool types always require an exact match
// regardless of tolerance. Forwards to the shared `isClose` family in
// Utils.h, which performs all arithmetic in double precision.
//
// Matrices, vectors and quaternions are included so that descendant transforms
// — notably `xformOp:transform` (a GfMatrix4d) — absorb the small
// floating-point drift typical of CAD re-exports under a nonzero tolerance,
// instead of forcing a bitwise-exact match that splits otherwise-identical
// instances. A descendant transform that differs by MORE than tolerance still
// blocks the merge; only sub-tolerance drift is absorbed.
static bool _valuesEqual(const VtValue& valA, const VtValue& valB, double tolerance)
{
    if (tolerance <= 0.0)
    {
        return valA == valB;
    }

    auto tryClose = [&](auto sample) -> std::optional<bool>
    {
        using T = decltype(sample);
        if (valA.IsHolding<T>() && valB.IsHolding<T>())
        {
            return isClose(valA.UncheckedGet<T>(), valB.UncheckedGet<T>(), tolerance);
        }
        return std::nullopt;
    };

#define USD_OPTIMIZE_TRY_CLOSE(T)                                                                                      \
    if (auto r = tryClose(T{}))                                                                                        \
        return *r;
    USD_OPTIMIZE_TOLERANCE_FLOAT_TYPES(USD_OPTIMIZE_TRY_CLOSE)
#undef USD_OPTIMIZE_TRY_CLOSE

    // All other types: exact match
    return valA == valB;
}


// True if `v` holds one of the floating-point value types that `tolerance`
// applies to (see USD_OPTIMIZE_TOLERANCE_FLOAT_TYPES). Used by the fingerprint
// pre-bucket to decide whether a value's contents may drift within tolerance
// (so only its array length is fingerprinted) or must match exactly.
static bool _isToleranceFloatType(const VtValue& v)
{
#define USD_OPTIMIZE_IS_HOLDING(T)                                                                                     \
    if (v.IsHolding<T>())                                                                                              \
        return true;
    USD_OPTIMIZE_TOLERANCE_FLOAT_TYPES(USD_OPTIMIZE_IS_HOLDING)
#undef USD_OPTIMIZE_IS_HOLDING
    return false;
}

#undef USD_OPTIMIZE_TOLERANCE_FLOAT_TYPES


// Recursively compare authored property values between two subtrees. Returns
// true if the subtrees are value-equivalent. xformOp properties are only
// skipped on the root prims (whose placement is expected to differ between
// instances); descendant transforms must still match (within tolerance) or the
// internal layout of the subtree would change beyond tolerance after
// instancing.
//
// Floating-point types — scalars, vectors, matrices, quaternions, and arrays
// of them — are compared within the given tolerance; integer/topology/string/
// token types require an exact match. An attribute that is authored (declared)
// but carries no authored value matches only another value-less attribute of
// the same name — it does not require a value on the other side.
static bool _subtreeValuesEqual(const UsdPrim& rootA, const UsdPrim& rootB, double tolerance, bool ignoreShaderOutputs)
{
    auto rangeA = UsdPrimRange(rootA);
    auto rangeB = UsdPrimRange(rootB);

    auto itA = rangeA.begin();
    auto itB = rangeB.begin();

    while (itA != rangeA.end() && itB != rangeB.end())
    {
        const UsdPrim& primA = *itA;
        const UsdPrim& primB = *itB;
        const bool isRoot = (primA == rootA);

        auto shouldSkip = [&](const UsdAttribute& attr) {
            return (isRoot && _isXformProperty(attr.GetName())) ||
                   (ignoreShaderOutputs && UsdShadeOutput::IsOutput(attr));
        };

        // Pass 1: every authored attr on A must match B. "Match" compares
        // authored *values*. An attribute that is authored (declared, so it
        // shows up in GetAuthoredAttributes / the structural hash) but carries
        // no authored value — e.g. an indexed primvar's `:indices` declared
        // without data — matches another value-less attribute of the same name;
        // it must NOT require a value on the other side. The previous code
        // unconditionally demanded an authored value on B, which wrongly split
        // otherwise-identical subtrees whenever such a declared-but-value-less
        // attribute was present on both copies.
        std::set<TfToken> seenOnA;
        for (const UsdAttribute& attrA : primA.GetAuthoredAttributes())
        {
            if (shouldSkip(attrA))
            {
                continue;
            }
            const TfToken& name = attrA.GetName();
            seenOnA.insert(name);

            const UsdAttribute attrB = primB.GetAttribute(name);
            const bool aHasValue = attrA.HasAuthoredValue();
            const bool bHasValue = attrB && attrB.HasAuthoredValue();
            if (aHasValue != bHasValue)
            {
                // One side authors a value, the other only declares the
                // attribute (or lacks it entirely): a genuine difference.
                return false;
            }
            if (!aHasValue)
            {
                // Neither side authors a value — nothing to compare.
                continue;
            }

            VtValue valA, valB;
            attrA.Get(&valA);
            attrB.Get(&valB);
            if (!_valuesEqual(valA, valB, tolerance))
            {
                return false;
            }
        }

        // Pass 2: catch attrs authored on B but not on A — pass 1 already
        // covered the intersection, so we only need a name-membership check.
        for (const UsdAttribute& attrB : primB.GetAuthoredAttributes())
        {
            if (shouldSkip(attrB))
            {
                continue;
            }
            if (!seenOnA.count(attrB.GetName()))
            {
                return false;
            }
        }

        ++itA;
        ++itB;
    }

    return (itA == rangeA.end() && itB == rangeB.end());
}


// A tolerance-independent fingerprint of a subtree's authored values, used to
// pre-bucket a structural group before the pairwise `_subtreeValuesEqual`
// partition. It hashes only content that must match bit-exactly for
// `_subtreeValuesEqual` to ever return true, regardless of tolerance — applying
// the same skip rules (root xformOps; shader outputs when ignored) and the same
// name-based, order-independent attribute set (attrs sorted by name, so the
// fingerprint does not depend on attribute iteration order):
//   - per authored attr: name + whether it has an authored value + its type;
//   - exact-compared types (int/topology arrays, strings, tokens, bools): the
//     full value;
//   - tolerance-compared float types: only the array length — the values may
//     drift within tolerance, but `isClose` still requires equal length;
//   - when `tolerance == 0` even float values are folded in, since equality is
//     then exact (and transitive).
//
// Because the fingerprint is a *necessary* condition for value-equality, two
// subtrees that satisfy `_subtreeValuesEqual` under any tolerance always share
// it: bucketing on it can never separate a true match (no false negatives). At
// `tolerance == 0` each bucket is exactly one value-equivalence class; at
// `tolerance > 0` a bucket is a superset that the pairwise pass refines.
static uint64_t _valueFingerprint(const UsdPrim& root, double tolerance, bool ignoreShaderOutputs)
{
    const bool exactOnly = (tolerance <= 0.0);
    uint64_t hash = kFnvOffset;

    for (const UsdPrim& prim : UsdPrimRange(root))
    {
        const bool isRoot = (prim == root);

        // Gather the participating authored attrs and sort by name so the
        // fingerprint is independent of attribute iteration order (matching
        // `_subtreeValuesEqual`'s name-based comparison).
        std::vector<UsdAttribute> attrs;
        for (const UsdAttribute& attr : prim.GetAuthoredAttributes())
        {
            const bool skip =
                (isRoot && _isXformProperty(attr.GetName())) || (ignoreShaderOutputs && UsdShadeOutput::IsOutput(attr));
            if (!skip)
            {
                attrs.push_back(attr);
            }
        }
        std::sort(attrs.begin(),
                  attrs.end(),
                  [](const UsdAttribute& a, const UsdAttribute& b)
                  { return a.GetName().GetString() < b.GetName().GetString(); });

        for (const UsdAttribute& attr : attrs)
        {
            hash = _fnvMix(hash, attr.GetName().GetString());

            const bool hasValue = attr.HasAuthoredValue();
            hash ^= hasValue ? 0x1ull : 0x2ull;
            hash *= kFnvPrime;
            if (!hasValue)
            {
                continue;
            }

            VtValue v;
            attr.Get(&v);
            hash = _fnvMix(hash, v.GetTypeName());

            if (!exactOnly && _isToleranceFloatType(v))
            {
                // Float contents may drift within tolerance — only the shape is
                // exact (`isClose` requires equal array length; scalar floats
                // contribute nothing beyond their type).
                if (v.IsArrayValued())
                {
                    hash ^= static_cast<uint64_t>(v.GetArraySize());
                    hash *= kFnvPrime;
                }
            }
            else
            {
                // Exact-compared content (or tolerance == 0): fold the value.
                hash ^= static_cast<uint64_t>(v.GetHash());
                hash *= kFnvPrime;
            }
        }

        // Domain separator between prims.
        hash ^= 0xee;
        hash *= kFnvPrime;
    }

    return hash;
}


// Partition a structurally-identical group of prims into value-equivalence
// classes. Two prims land in the same class iff `_subtreeValuesEqual` holds
// between them (xformOp values on the root prim ignored, shader outputs
// optionally ignored, floating-point values compared within `tolerance`).
//
// To keep this near-linear on large value-distinct groups (parametric CAD —
// the case this op targets), members are first bucketed by a tolerance-
// independent value fingerprint, and the pairwise `_subtreeValuesEqual` compare
// then runs only *within* a bucket. Members in different buckets differ on
// exact-typed content (or a float array length), so they can never be
// value-equal — scoping the pairwise pass to a bucket loses no merges. The
// fingerprint is a 64-bit hash, so the pairwise compare runs for ALL tolerances
// (including `tolerance == 0`) to verify it: in a lossless op a hash collision
// must never silently merge two genuinely-distinct subtrees. At `tolerance == 0`
// the bucket is already (modulo a collision) one exact-value class, so the verify
// is ~one compare-to-representative per member — cheap, and it splits the rare
// collision instead of trusting the hash as the final word.
//
// The partition is order-independent w.r.t. the *merge outcome*: within a
// bucket every class is formed from members mutually equivalent to the class's
// representative (`cls.front()`), so a group containing several value-variants
// yields one class per variant regardless of member ordering. `isClose` is not
// transitive, so with `tolerance > 0` classes are defined by equivalence to the
// representative, not by global clustering — matching the prior contract; the
// only behavioural change from the bucketing is performance.
static std::vector<PrimVector> _partitionByValues(const PrimVector& group, double tolerance, bool ignoreShaderOutputs)
{
    // Bucket by fingerprint, preserving first-seen order for stable output.
    std::unordered_map<uint64_t, PrimVector> buckets;
    std::vector<uint64_t> bucketOrder;
    for (const UsdPrim& prim : group)
    {
        const uint64_t fp = _valueFingerprint(prim, tolerance, ignoreShaderOutputs);
        auto [it, inserted] = buckets.try_emplace(fp);
        if (inserted)
        {
            bucketOrder.push_back(fp);
        }
        it->second.push_back(prim);
    }

    std::vector<PrimVector> classes;
    for (const uint64_t fp : bucketOrder)
    {
        PrimVector& bucket = buckets[fp];

        // Refine the bucket into value-equivalence classes with the pairwise
        // compare — for ALL tolerances. The fingerprint only pre-buckets (members
        // of other buckets differ on exact-typed content, so cross-bucket
        // comparison is never needed); the pairwise pass is what actually verifies
        // value-equality, so a 64-bit fingerprint collision can never silently
        // merge distinct subtrees. At `tolerance == 0` the bucket is
        // near-homogeneous, so this is ~one compare-to-representative per member.
        std::vector<PrimVector> bucketClasses;
        for (const UsdPrim& prim : bucket)
        {
            bool placed = false;
            for (PrimVector& cls : bucketClasses)
            {
                // cls.front() is the class representative (eventual prototype).
                if (_subtreeValuesEqual(cls.front(), prim, tolerance, ignoreShaderOutputs))
                {
                    cls.push_back(prim);
                    placed = true;
                    break;
                }
            }
            if (!placed)
            {
                bucketClasses.push_back({ prim });
            }
        }
        for (PrimVector& cls : bucketClasses)
        {
            classes.push_back(std::move(cls));
        }
    }

    return classes;
}


// Walk one BFS level and merge any newly discovered duplicate groups into
// `outDuplicates`. Returns the next level's prims (children of every prim that
// was NOT pruned, with material scopes filtered out).
//
// Structural grouping and value partitioning are coupled here on purpose:
// only the *duplicates* of a value-equivalence class (size >= 2) are pruned
// from further traversal. Three kinds of prim therefore keep contributing
// children to the next level:
//   - prims that grouped structurally but failed value comparison, or were a
//     lone value-variant — their nested duplicate subtrees are still found;
//   - prims excluded from merging because they carry refs/payloads;
//   - the prototype of each merged class. Descending into the prototype lets
//     us consolidate duplicates *inside* it into nested instanceable
//     references; every instance that references the prototype then inherits
//     that nested structure, so shared inner content is deduplicated once.
//
// Pruning on a bare structural match (the original behaviour) silently hid
// nested duplicates whenever the enclosing structural group was later rejected
// by value refinement; pruning the prototype as well (the behaviour before
// nested-instance support) stopped the op one level deep per branch and never
// built a deep instance library.
static PrimVector _processLevel(const PrimVector& currentLevel,
                                HierarchyMap& outDuplicates,
                                double tolerance,
                                bool ignoreShaderOutputs)
{
    // Group prims by their structural hash. The hash always returns a
    // non-empty hex string, so every non-material-related prim gets keyed.
    std::unordered_map<std::string, PrimVector> groups;

    for (const UsdPrim& prim : currentLevel)
    {
        if (_isMaterialRelated(prim))
        {
            continue;
        }
        groups[_structuralHash(prim)].push_back(prim);
    }

    // Merged duplicates (not their prototype). Only these are pruned from the
    // next BFS level: their children are deleted and replaced by the reference
    // to the prototype, so there is nothing left to discover under them. The
    // prototype is deliberately left out so the BFS descends into it.
    SdfPathSet pruned;
    size_t totalDropped = 0;

    for (auto& [key, group] : groups)
    {
        if (group.size() < 2)
        {
            continue;
        }

        // Prims that already carry refs/payloads are excluded from the
        // duplicate set so we don't overwrite an already-customised instance.
        PrimVector valid;
        valid.reserve(group.size());
        for (const UsdPrim& p : group)
        {
            if (!_hasReferencesOrPayloads(p))
            {
                valid.push_back(p);
            }
        }
        if (valid.size() < 2)
        {
            continue;
        }

        // Partition the structural group into value-equivalence classes and
        // emit a prototype + duplicates for every class with >= 2 members. A
        // group with multiple value-variants therefore yields one prototype
        // per variant instead of collapsing to a single front()-comparison.
        const std::vector<PrimVector> classes = _partitionByValues(valid, tolerance, ignoreShaderOutputs);
        for (size_t classIndex = 0; classIndex < classes.size(); ++classIndex)
        {
            const PrimVector& cls = classes[classIndex];
            if (cls.size() < 2)
            {
                // Lone value-variant within a multi-member structural group:
                // structurally identical to its peers but value-distinct, so
                // it has no duplicate to merge with. Tally it for the verbose
                // diagnostic below; it still flows into the next BFS level.
                ++totalDropped;
                continue;
            }

            const SdfPath prototype = cls.front().GetPath();
            // Every SdfPath is unique within a BFS level and across levels: a
            // duplicate is pruned (so it never reappears) and a prototype only
            // ever descends into its own children, so the same path cannot be
            // chosen as a prototype twice. This entry is therefore freshly
            // default-constructed and empty here, so `reserve` is an exact hint.
            SdfPathVector& duplicates = outDuplicates[prototype];
            duplicates.reserve(cls.size() - 1);
            // The prototype is intentionally NOT added to `pruned`: the BFS
            // descends into it to consolidate nested duplicates. Only the
            // duplicates are pruned.
            for (size_t i = 1; i < cls.size(); ++i)
            {
                duplicates.push_back(cls[i].GetPath());
                pruned.insert(cls[i].GetPath());
            }

            USD_OPTIMIZE_LOG_VERBOSE("Duplicate group '%s' (variant %zu/%zu): prototype=%s, duplicates=%zu",
                                     key.c_str(),
                                     classIndex + 1,
                                     classes.size(),
                                     prototype.GetAsString().c_str(),
                                     duplicates.size());
        }
    }

    if (totalDropped > 0)
    {
        USD_OPTIMIZE_LOG_VERBOSE("Value refinement: %zu value-variant class(es) had no duplicate to merge at this level.",
                                 totalDropped);
    }

    // Build the next BFS level from the children of every prim that was NOT
    // pruned, skipping material-related prims for the same reason we skip them
    // at the per-prim filter. Prototypes, lone variants, value-mismatched
    // prims, and ref/payload-bearing prims all contribute their children, so
    // nested duplicates inside any of them are still discovered.
    PrimVector nextLevel;
    for (const UsdPrim& prim : currentLevel)
    {
        if (pruned.count(prim.GetPath()) > 0)
        {
            continue;
        }
        if (_isMaterialRelated(prim))
        {
            continue;
        }
        for (const UsdPrim& child : prim.GetChildren())
        {
            nextLevel.push_back(child);
        }
    }
    return nextLevel;
}


// Collect the BFS starting prims. If user-supplied paths are given, those
// are the roots; otherwise we start from the children of the default prim
// (matching the Python processor's default behaviour).
static PrimVector _resolveStartingPrims(const UsdStageWeakPtr& stage, const std::vector<std::string>& paths)
{
    PrimVector starting;
    if (!paths.empty())
    {
        for (const std::string& s : paths)
        {
            const SdfPath path(s);
            if (!path.IsAbsolutePath() || !path.IsPrimPath())
            {
                USD_OPTIMIZE_LOG_WARN("Skipping non-absolute prim path: %s", s.c_str());
                continue;
            }
            UsdPrim prim = stage->GetPrimAtPath(path);
            if (!prim || !prim.IsValid())
            {
                USD_OPTIMIZE_LOG_WARN("Path not found on stage: %s", s.c_str());
                continue;
            }
            // The user-supplied paths are *subtree roots* — the BFS starts
            // at their children (the same level the default prim's children
            // sit at when no paths are given).
            for (const UsdPrim& child : prim.GetChildren())
            {
                starting.push_back(child);
            }
        }
        return starting;
    }

    UsdPrim defaultPrim = stage->GetDefaultPrim();
    if (!defaultPrim || !defaultPrim.IsValid())
    {
        // Not an error: a stage without a default prim is legal USD, and
        // callers may legitimately invoke this operation against a global
        // pipeline that doesn't always set one. The result is a safe no-op —
        // we surface a warning so the caller can decide whether they meant
        // to provide `paths`, but the operation succeeds.
        USD_OPTIMIZE_LOG_WARN(
            "Stage has no default prim; nothing to deduplicate. Provide `paths` to restrict to a subtree if this is unexpected.");
        return starting;
    }
    for (const UsdPrim& child : defaultPrim.GetChildren())
    {
        starting.push_back(child);
    }
    return starting;
}


// Replace each duplicate with an instanceable internal reference to the
// prototype. Children of the duplicate are deleted first (mirroring the
// Python processor and OrganizePrototypes' `_convertProtoToInstance`).
static bool _applyInternalReferences(const UsdStageWeakPtr& stage, const HierarchyMap& hierarchies)
{
    bool allOk = true;
    size_t total = 0;
    for (const auto& [_proto, dups] : hierarchies)
    {
        total += dups.size();
    }
    USD_OPTIMIZE_LOG_INFO("Authoring %zu instanceable internal references.", total);

    for (const auto& [prototype, duplicates] : hierarchies)
    {
        for (const SdfPath& dupPath : duplicates)
        {
            UsdPrim dup = stage->GetPrimAtPath(dupPath);
            if (!dup || !dup.IsValid())
            {
                USD_OPTIMIZE_LOG_WARN("Skipping invalid duplicate prim: %s", dupPath.GetAsString().c_str());
                allOk = false;
                continue;
            }

            // Collect children up front because we'll mutate during deletion.
            PrimVector childrenToDelete;
            for (const UsdPrim& child : dup.GetChildren())
            {
                childrenToDelete.push_back(child);
            }
            _deletePrims(stage, childrenToDelete, true /* deactivate fallback */);

            UsdReferences refs = dup.GetReferences();
            refs.ClearReferences();
            if (!refs.AddInternalReference(prototype))
            {
                USD_OPTIMIZE_LOG_WARN("Failed to add internal reference on %s -> %s",
                                      dupPath.GetAsString().c_str(),
                                      prototype.GetAsString().c_str());
                allOk = false;
                continue;
            }
            dup.SetInstanceable(true);
        }
    }
    return allOk;
}


DeduplicateHierarchiesOperation::DeduplicateHierarchiesOperation()
    : Operation("deduplicateHierarchies",
                "Deduplicate Hierarchies",
                "Find duplicate prim hierarchies and replace duplicates with instanceable "
                "internal references to a prototype. Groups prims by subtree shape, then "
                "partitions each group into value-equivalence classes so that a set of "
                "structurally-identical copies with multiple value-variants yields one "
                "prototype per variant. Recurses into each prototype so nested duplicates "
                "are consolidated into nested instanceable references.")
    , m_paths()
    , m_tolerance(0.001)
    , m_ignoreShaderOutputs(true)
    , m_maxDepth(0)
{
    addArgument("paths",
                "Prim Paths",
                kDisplayTypePrimPaths,
                "Optional subtree roots. Empty = walk children of the default prim.",
                m_paths);

    addArgument("tolerance",
                "Tolerance",
                kDisplayTypeFloat,
                "Acceptable difference for floating-point properties when comparing subtrees: "
                "scalar float/double/half, vectors, matrices (including descendant "
                "xformOp:transform), quaternions, and arrays of any of these (points, "
                "normals, UVs, etc.). The value is in stage units. Integer/topology indices, "
                "strings, tokens and bools always require an exact match regardless of "
                "tolerance. Set to 0 for bitwise-exact comparison.",
                m_tolerance);

    addArgument("ignoreShaderOutputs",
                "Ignore Shader Outputs",
                kDisplayTypeBool,
                "Skip shader output attributes (outputs:surface, outputs:displacement, etc.) "
                "during value comparison. These often differ between material instances even "
                "when the geometry is identical. Enabled by default.",
                m_ignoreShaderOutputs);

    addArgument("maxDepth",
                "Max Depth",
                kDisplayTypeInt,
                "Maximum number of breadth-first levels to descend, counting from the "
                "children of the default prim (or of `paths`) as level 1. 0 (the default) "
                "means unbounded. Because the operation recurses into each prototype to "
                "build a nested-instance library, deep hierarchies can reach many levels; "
                "cap this to bound runtime or to avoid consolidating very deeply nested "
                "instances.",
                m_maxDepth);
}


DeduplicateHierarchiesOperation::~DeduplicateHierarchiesOperation() = default;


std::string DeduplicateHierarchiesOperation::getAuthor() const
{
    return USD_OPTIMIZE_TO_STRING(USD_OPTIMIZE_PLUGIN_AUTHOR);
}


UsdOptimizePluginVersion DeduplicateHierarchiesOperation::getVersion() const
{
    return { 1, 0, 0 };
}


std::string DeduplicateHierarchiesOperation::getCategory() const
{
    return s_categoryDedupHierarchies;
}


std::string DeduplicateHierarchiesOperation::getDisplayGroup() const
{
    return s_displayGroupStage;
}


bool DeduplicateHierarchiesOperation::getSupportsAnalysis() const
{
    return true;
}


HierarchyMap DeduplicateHierarchiesOperation::_findDuplicates()
{
    const UsdStageWeakPtr stage = getUsdStage();
    if (!stage)
    {
        USD_OPTIMIZE_LOG_ERROR("No USD stage available.");
        return {};
    }

    PrimVector currentLevel = _resolveStartingPrims(stage, m_paths);
    if (currentLevel.empty())
    {
        USD_OPTIMIZE_LOG_INFO("No prims to scan; nothing to deduplicate.");
        return {};
    }

    USD_OPTIMIZE_LOG_VERBOSE(
        "Grouping by structural hash (subtree shape + types + authored property names), "
        "then partitioning each group into value-equivalence classes.");

    HierarchyMap hierarchies;
    int level = 1;
    while (!currentLevel.empty())
    {
        if (m_maxDepth > 0 && level > m_maxDepth)
        {
            USD_OPTIMIZE_LOG_VERBOSE("Reached maxDepth=%d; stopping breadth-first traversal.", m_maxDepth);
            break;
        }
        USD_OPTIMIZE_LOG_VERBOSE("Scanning level %d (%zu prims)", level, currentLevel.size());
        currentLevel = _processLevel(currentLevel, hierarchies, m_tolerance, m_ignoreShaderOutputs);
        ++level;
    }

    if (hierarchies.empty())
    {
        USD_OPTIMIZE_LOG_INFO("No duplicate hierarchies found.");
        return {};
    }

    return hierarchies;
}


OperationResult DeduplicateHierarchiesOperation::executeAnalysisImpl()
{
    HierarchyMap hierarchies = _findDuplicates();

    // Convert to a JSON object: { "analysis": { "proto_path": ["dup1", "dup2", ...], ... } }
    JsObject analysisObj;
    for (const auto& [prototype, duplicates] : hierarchies)
    {
        analysisObj[prototype.GetAsString()] = _toJson(duplicates);
    }

    JsObject resultJson;
    resultJson["analysis"] = std::move(analysisObj);

    OperationResult result{ true };
    result.output = getCStr(JsWriteToString(resultJson));

    return result;
}


OperationResult DeduplicateHierarchiesOperation::executeImpl()
{
    HierarchyMap hierarchies = _findDuplicates();

    if (hierarchies.empty())
    {
        return { true };
    }

    const bool ok = _applyInternalReferences(getUsdStage(), hierarchies);
    return { ok };
}


} // namespace usd_optimize
