# SPDX-FileCopyrightText: Copyright (c) 2025-2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#

from functools import partial
from typing import ClassVar, List, Mapping

from pxr import Usd
from usd_optimize.core import analysis
from usd_validation_nvidia import Suggestion, capabilities, register_requirements

from .base_usd_optimize_checker import BaseUsdOptimizeChecker, Parameter

# Usd Optimize Constants
MODE_HIDE = 3


@register_requirements(capabilities.GeometryRequirements.VG_003)
class OccludedMeshesChecker(BaseUsdOptimizeChecker):
    """
    Uses Usd Optimize to analyze a scene checking for occluded meshes.

    Parameters:
        USE_GPU: Enable GPU-accelerated occlusion detection. Default: False.
        CHECK_TRANSPARENCY: Consider material transparency when detecting occlusion. Default: True.
        CLUSTERED: Split the stage into clusters of meshes with overlapping bounding boxes and check visibility per cluster, improving both accuracy and performance by reducing the number of meshes compared at the same time. Default: True.
        MINIMUM_GAP_SIZE: The minimum gap size for the background grid spacing. Gaps smaller than this are considered closed. Default: 0.01.
        MAXIMUM_GRID_RESOLUTION: The maximum number of cells along the longest axis of the visibility grid. Default: 500.0.
    """

    OPERATION_NAME: str = "findOccludedMeshes"
    PARAMETERS: ClassVar[Mapping[str, Parameter]] = {
        "USE_GPU": Parameter(default=False, op_arg="useGpu"),
        "CHECK_TRANSPARENCY": Parameter(default=True, op_arg="checkTransparency"),
        "CLUSTERED": Parameter(default=True, op_arg="clustered"),
        "MINIMUM_GAP_SIZE": Parameter(default=0.01, op_arg="minimumGapSize"),
        "MAXIMUM_GRID_RESOLUTION": Parameter(default=500.0, op_arg="maximumGridResolution"),
    }

    @classmethod
    def _remove_occluded_meshes(
        cls,
        usdStage: Usd.Stage,
        _: Usd.Prim,
        use_gpu: bool = False,
        check_transparency: bool = True,
        clustered: bool = True,
        minimum_gap_size: float = 0.01,
        maximum_grid_resolution: float = 500.0,
    ) -> None:
        """Remove occluded meshes using Usd Optimize.

        Args:
            usdStage: The USD stage to operate on
            _: Unused prim argument (required by Suggestion callable signature)
            use_gpu: Whether to use GPU acceleration
            check_transparency: Whether to consider material transparency
            clustered: Whether to cluster meshes before visibility checking
            minimum_gap_size: The minimum gap size for the background grid
            maximum_grid_resolution: The maximum grid resolution for visibility checking
        """
        # Configure operation
        # Need to pass all meshes involved in occluded mesh detection,
        # not just occluded mesh, so easiest just to work on full scene
        operations: List[analysis.OperationConfig] = [
            analysis.OperationConfig(
                cls.OPERATION_NAME,
                args={
                    "action": MODE_HIDE,
                    "useGpu": use_gpu,
                    "checkTransparency": check_transparency,
                    "clustered": clustered,
                    "minimumGapSize": minimum_gap_size,
                    "maximumGridResolution": maximum_grid_resolution,
                },
            ),
        ]

        # Execute the optimization via Usd Optimize.
        analysis.optimize(usdStage, operations)

    def _CheckStage(self, usdStage: Usd.Stage, analysis_data: dict):
        """Check a stage for occluded meshes"""

        occluded_mesh_paths = analysis_data["occludedMeshes"]
        occluded_mesh_count = len(occluded_mesh_paths)

        if occluded_mesh_count > 0:
            suffix = "" if occluded_mesh_count == 1 else "es"
            message: str = f"Found {occluded_mesh_count} occluded mesh{suffix}"

            args = self._effective_args()
            self._AddWarning(
                message=message,
                at=usdStage.GetPrimAtPath("/"),
                suggestion=Suggestion(
                    message="Remove occluded meshes using Usd Optimize",
                    callable=partial(
                        self._remove_occluded_meshes,
                        use_gpu=args["useGpu"],
                        check_transparency=args["checkTransparency"],
                        clustered=args["clustered"],
                        minimum_gap_size=args["minimumGapSize"],
                        maximum_grid_resolution=args["maximumGridResolution"],
                    ),
                ),
            )
