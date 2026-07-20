# SPDX-FileCopyrightText: Copyright (c) 2025-2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#

from functools import partial
from typing import List

from pxr import Usd
from usd_optimize.core import analysis
from usd_validation_nvidia import Suggestion, capabilities, register_requirements

from .base_usd_optimize_checker import BaseUsdOptimizeChecker

# Usd Optimize Constants
MODE_DEDUPLICATE = 0


@register_requirements(capabilities.MaterialsRequirements.VM_D_001)
class DuplicateMaterialsChecker(BaseUsdOptimizeChecker):
    """
    Finds duplicate materials; fixed by deduplicating them.
    """

    OPERATION_NAME: str = "optimizeMaterials"

    @classmethod
    def _deduplicate_materials(cls, usdStage: Usd.Stage, prim: Usd.Prim, duplicates: list) -> None:

        # Configure Optimize Materials operation
        operations: List[analysis.OperationConfig] = [
            analysis.OperationConfig(
                cls.OPERATION_NAME,
                args={"materialPrimPaths": duplicates, "mode": MODE_DEDUPLICATE, "analysisCheckPrimvars": False},
            ),
        ]

        # Execute the optimization via Usd Optimize.
        analysis.optimize(usdStage, operations)

    def _CheckStage(self, usdStage: Usd.Stage, analysis_data: dict):
        """Check a stage for duplicate materials"""

        # Duplicates will always exist in the result, if we got this far.
        duplicate_groups: List[List[str]] = analysis_data["duplicates"]

        # Duplicate groups is a list of lists - each list is a set of duplicate
        # materials.
        for duplicates in duplicate_groups:

            # Consider the first material the "main" one, and everything else to be
            # a duplicate of that.
            material_paths: List[str] = sorted(duplicates)
            material_path: str = material_paths[0]
            material_prim: Usd.Prim = usdStage.GetPrimAtPath(material_path)
            count: int = len(duplicates) - 1

            message: str = ""
            if count == 1:
                message = f"There is 1 duplicate of {material_path}"
            else:
                message = f"There are {count} duplicates of {material_path}"

            self._AddWarning(
                message=message,
                at=material_prim,
                suggestion=Suggestion(
                    message="Deduplicate materials using Usd Optimize",
                    callable=partial(self._deduplicate_materials, duplicates=material_paths),
                ),
            )
