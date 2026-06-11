# SPDX-FileCopyrightText: Copyright (c) 2025-2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#

from functools import partial
from typing import List

from pxr import Usd
from usd_optimize.core import analysis
from usd_validation_nvidia import Suggestion

from .base_usd_optimize_checker import BaseUsdOptimizeChecker

# Constants
DUPLICATE_METHOD_INSTANCEABLEREFERENCE = 2


class BaseDuplicateGeometryChecker(BaseUsdOptimizeChecker):
    """Base checker for finding duplicate geometry"""

    OPERATION_NAME: str = "deduplicateGeometry"

    @classmethod
    def _deduplicate_geometry(cls, usdStage: Usd.Stage, _: Usd.Stage, duplicates: list) -> None:

        # Copy the operation arguments and update the specific prims to dedup
        args = cls.OPERATION_ARGS.copy()
        args["meshPrimPaths"] = duplicates

        # Configure operation
        operations: List[analysis.OperationConfig] = [
            analysis.OperationConfig(cls.OPERATION_NAME, args=args),
        ]

        # Execute the optimization via Usd Optimize.
        analysis.optimize(usdStage, operations)

    def _CheckStage(self, usdStage: Usd.Stage, analysis_data: dict):
        """Generate issues based on the deduplicate analysis"""

        # Duplicates will always exist in the result, if we got this far.
        duplicate_groups: List[List[str]] = analysis_data

        # Duplicate groups is a list of lists, each being a set of duplicate
        # geometric prims
        for duplicates in duplicate_groups:

            count: int = len(duplicates)
            prim_path: str = duplicates[0]

            suffix: str = "s" if count != 2 else ""
            message = f"{prim_path} has {count - 1} duplicate{suffix}"

            self._AddWarning(
                message=message,
                at=usdStage,
                suggestion=Suggestion(
                    message="Deduplicate geometry using Usd Optimize",
                    callable=partial(self._deduplicate_geometry, duplicates=duplicates),
                ),
            )
