# SPDX-FileCopyrightText: Copyright (c) 2025-2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#

from usd_validation_nvidia import capabilities, register_requirements

from .base_duplicate_geometry_checker import DUPLICATE_METHOD_INSTANCEABLEREFERENCE, BaseDuplicateGeometryChecker


@register_requirements(capabilities.GeometryRequirements.VG_022)
class DuplicateGeometryChecker(BaseDuplicateGeometryChecker):
    """
    Find geometric prims that are duplicates; fixed by creating instances.
    """

    # Default arguments for the command
    OPERATION_ARGS = {
        # Default Args
        "meshPrimPaths": [],
        "considerDeepTransforms": True,
        "tolerance": 0.05,
        "duplicateMethod": DUPLICATE_METHOD_INSTANCEABLEREFERENCE,
        "useGpu": False,
        # Fuzzy Args
        "fuzzy": False,
        "allowScaling": False,
    }
