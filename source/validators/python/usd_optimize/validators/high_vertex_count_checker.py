# SPDX-FileCopyrightText: Copyright (c) 2025-2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#

from pxr import Usd
from usd_validation_nvidia import capabilities, register_requirements

from .base_usd_optimize_checker import BaseUsdOptimizeChecker


@register_requirements(capabilities.GeometryRequirements.VG_021)
class HighVertexCountChecker(BaseUsdOptimizeChecker):
    """
    Check a stage for meshes with high or extreme vertex counts.
    """

    OPERATION_NAME: str = "countVertices"
    OPERATION_ARGS: dict = {}

    LEVEL_HIGH: int = 100000
    LEVEL_VERY_HIGH: int = 500000
    LEVEL_EXTREME: int = 1000000

    def _GetArgs(self):
        """Custom GetArgs function

        Allows configuring the thresholds when testing the operation
        """
        return {"high": self.LEVEL_HIGH, "veryHigh": self.LEVEL_VERY_HIGH, "extreme": self.LEVEL_EXTREME}

    def _GenerateWarning(self, prim: Usd.Prim, count: int, level: str):
        """Add a warning based on the prim/count"""

        self._AddWarning(message=f"Mesh has {level} vertex count ({count})", at=prim)

    def _CheckStage(self, usdStage: Usd.Stage, analysis_data: dict):
        """
        Process the Usd Optimize analysis of empty leaves and log warnings/suggestions.
        """

        for path, count in analysis_data["high"].items():
            self._GenerateWarning(usdStage.GetPrimAtPath(path), count, "high")

        for path, count in analysis_data["veryHigh"].items():
            self._GenerateWarning(usdStage.GetPrimAtPath(path), count, "very high")

        for path, count in analysis_data["extreme"].items():
            self._GenerateWarning(usdStage.GetPrimAtPath(path), count, "extreme")
