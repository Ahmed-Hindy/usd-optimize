# SPDX-FileCopyrightText: Copyright (c) 2025-2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#

from pxr import Usd
from usd_validation_nvidia import capabilities, register_requirements

from .base_usd_optimize_checker import BaseUsdOptimizeChecker


@register_requirements(capabilities.GeometryRequirements.VG_RTX_002)
class RtxMeshCountChecker(BaseUsdOptimizeChecker):
    """
    Check if the number of RTX meshes exceeds recommended limits.
    """

    OPERATION_NAME: str = "rtxMeshCount"

    RTX_UNIQUE_MESH_COUNT_LIMIT: int = 438000

    def _CheckStage(self, usdStage: Usd.Stage, analysis_data: dict):
        # verify that the analysis data contains the number of unique RTX meshes
        rtx_unique_mesh_count = analysis_data.get("rtxUniqueMeshCount")
        if rtx_unique_mesh_count is None:
            self._AddFailedCheck(message="Analysis data does not contain RTX unique mesh count")
            return

        # exceeds recommended limit?
        if rtx_unique_mesh_count > self.RTX_UNIQUE_MESH_COUNT_LIMIT:
            self._AddWarning(
                message=f"Number of unique RTX meshes ({rtx_unique_mesh_count}) exceeds the recommended limit of {self.RTX_UNIQUE_MESH_COUNT_LIMIT}.",
            )
