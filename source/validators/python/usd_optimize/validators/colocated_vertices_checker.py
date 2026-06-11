# SPDX-FileCopyrightText: Copyright (c) 2025-2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#

from functools import partial
from typing import List

from pxr import Usd
from usd_optimize.core import analysis
from usd_validation_nvidia import Suggestion, capabilities, register_requirements

from .base_usd_optimize_checker import BaseUsdOptimizeChecker


@register_requirements(capabilities.GeometryRequirements.VG_016, override=True)
class ColocatedVerticesChecker(BaseUsdOptimizeChecker):
    """
    Check mesh prims for colocated vertices, returns all prims with colocated vertices as a single warning with an option to fix via scene optimizer operation.
    """

    OPERATION_NAME: str = "meshCleanup"

    @classmethod
    def _mesh_merge_vertices(cls, usdStage: Usd.Stage, prim: Usd.Prim) -> None:
        """
        Cleanup meshes by merging vertices using Usd Optimize
        """

        # Configure mesh cleanup
        operations: List[analysis.OperationConfig] = [
            analysis.OperationConfig(
                cls.OPERATION_NAME,
                args={
                    "mergeVertices": True,
                    "tolerance": 0.0,
                    "mergeBoundaries": True,
                    "mergeNeighbors": True,
                    "contractDegenerateEdges": False,
                    "removeDegenerateFaces": False,
                    "makeManifold": False,
                    "removeIsolatedVertices": False,
                    "removeDuplicateFaces": False,
                },
            ),
        ]

        # Execute the optimization via Usd Optimize.
        analysis.optimize(usdStage, operations)

    def _CheckStage(self, usdStage: Usd.Stage, analysis_data: dict):
        """
        Process the Usd Optimize analysis of mesh cleanups
        """

        # Retrieve problem count
        meshesWithMergeableVertices = analysis_data["meshesWithMergeableVertices"]

        if meshesWithMergeableVertices > 0:
            suffix = "es" if meshesWithMergeableVertices > 1 else ""
            message: str = f"Found {meshesWithMergeableVertices} mesh{suffix} with mergeable vertices to fix"
            self._AddWarning(
                # requirement=cap.GeometryRequirements.VG_016,
                message=message,
                at=usdStage.GetPrimAtPath("/"),
                suggestion=Suggestion(
                    message="Fix meshes with coincident vertices using Usd Optimize",
                    callable=partial(self._mesh_merge_vertices),
                ),
            )
