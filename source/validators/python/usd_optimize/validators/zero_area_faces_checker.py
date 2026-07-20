# SPDX-FileCopyrightText: Copyright (c) 2025-2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#

from functools import partial
from typing import List

from pxr import Usd
from usd_optimize.core import analysis
from usd_validation_nvidia import Suggestion, capabilities, register_requirements

from .base_usd_optimize_checker import BaseUsdOptimizeChecker


@register_requirements(capabilities.GeometryRequirements.VG_019, override=True)
class ZeroAreaFacesChecker(BaseUsdOptimizeChecker):
    """
    Check mesh prims for any zero area faces, returns all prims that have zero
    area faces as single warning with an option to fix using the scene optimizer
    operation.
    """

    OPERATION_NAME: str = "meshCleanup"

    @classmethod
    def _mesh_remove_zero_area_faces(cls, usdStage: Usd.Stage, prim: Usd.Prim) -> None:
        """
        Cleanup meshes by removing zero area faces using Usd Optimize
        """

        # TODO: Configure settings to remove zero area faces

        # Configure mesh cleanup
        operations: List[analysis.OperationConfig] = [
            analysis.OperationConfig(
                cls.OPERATION_NAME,
                args={
                    "mergeVertices": False,
                    "tolerance": 0.0,
                    "contractDegenerateEdges": True,
                    "removeDegenerateFaces": True,
                    "makeManifold": False,
                    "removeIsolatedVertices": False,
                    "mergeBoundaries": False,
                    "mergeNeighbors": False,
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
        meshesWithDegenerateFaces = analysis_data["meshesWithDegenerateFaces"]

        if meshesWithDegenerateFaces > 0:
            suffix = "es" if meshesWithDegenerateFaces > 1 else ""
            message: str = f"Found {meshesWithDegenerateFaces} zero area faces mesh{suffix} to fix"
            self._AddWarning(
                # requirement=cap.GeometryRequirements.VG_019,
                message=message,
                at=usdStage.GetPrimAtPath("/"),
                suggestion=Suggestion(
                    message="Fix zero area faces meshes using Usd Optimize",
                    callable=partial(self._mesh_remove_zero_area_faces),
                ),
            )

            # In verbose mode, list each mesh with zero area faces individually.
            self._AddVerbosePrimWarnings(
                usdStage,
                analysis_data.get("meshesWithDegenerateFacesPaths", []),
                "Mesh with zero area faces found",
            )
