# SPDX-FileCopyrightText: Copyright (c) 2025-2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#

from functools import partial
from typing import Any, ClassVar, Mapping

from pxr import Usd
from usd_optimize.core import analysis
from usd_validation_nvidia import Suggestion, capabilities, register_requirements

from .base_usd_optimize_checker import BaseUsdOptimizeChecker, Parameter


@register_requirements(capabilities.GeometryRequirements.VG_012)
class SmallMeshChecker(BaseUsdOptimizeChecker):
    """
    Uses Usd Optimize to analyze a scene checking for meshes with extents
    below a configurable size threshold.

    Parameters:
        SIZE_THRESHOLD: The minimum extent size a mesh can have before it is
            considered small. Default: 0.001.
    """

    OPERATION_NAME: str = "removeSmallGeometry"
    OPERATION_ARGS: ClassVar[Mapping[str, Any]] = {"removeMethod": 1, "detectionMethod": 0}
    PARAMETERS: ClassVar[Mapping[str, Parameter]] = {
        "SIZE_THRESHOLD": Parameter(default=0.001, op_arg="threshold"),
    }

    @classmethod
    def _optimize_stage(cls, usdStage: Usd.Stage, _: Usd.Prim, operation_configs: list) -> None:
        """Remove small meshes using the analysis-derived operation configs.

        Args:
            usdStage: The USD stage to operate on
            _: Unused prim argument (required by Suggestion callable signature)
            operation_configs: Operation configs from analysis result
        """
        analysis.optimize(usdStage, operation_configs)

    def _CheckStage(self, usdStage: Usd.Stage, analysis_data: dict):
        """Check a stage for small meshes below the size threshold."""
        small_mesh_paths = analysis_data.get("smallGeometry", [])

        if small_mesh_paths:
            threshold = self._effective_args()["threshold"]
            suffix = "" if len(small_mesh_paths) == 1 else "es"
            self._AddWarning(
                message=f"Stage contains {len(small_mesh_paths)} mesh{suffix} below size threshold {threshold}",
                at=usdStage.GetPrimAtPath("/"),
                suggestion=Suggestion(
                    message="Remove small meshes using Usd Optimize",
                    callable=partial(self._optimize_stage, operation_configs=self.suggested_operations),
                ),
            )

        for prim_path in small_mesh_paths:
            self._AddWarning(
                message="Small mesh found",
                at=usdStage.GetPrimAtPath(prim_path),
            )
