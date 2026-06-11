# SPDX-FileCopyrightText: Copyright (c) 2025-2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#

from typing import List

from pxr import Usd
from usd_optimize.core import analysis
from usd_validation_nvidia import Suggestion, capabilities, register_requirements

from .base_usd_optimize_checker import BaseUsdOptimizeChecker

# Constants
MODE_BLOCK = 1


@register_requirements(capabilities.GeometryRequirements.VG_033)
class UnusedUVsChecker(BaseUsdOptimizeChecker):
    """
    Check a stage for unused texture coordinate primvars.
    """

    OPERATION_NAME: str = "removeUnusedUVs"
    OPERATION_ARGS: dict = {}

    @classmethod
    def _remove_uvs(cls, usdStage: Usd.Stage, attribute: Usd.Attribute) -> None:
        """
        Remove an unused UV attribute
        """

        operations: List[analysis.OperationConfig] = [
            analysis.OperationConfig(
                cls.OPERATION_NAME, args={"paths": [str(attribute.GetPrimPath())], "mode": MODE_BLOCK}
            ),
        ]

        # Execute the optimization via Usd Optimize.
        analysis.optimize(usdStage, operations)

    def _CheckStage(self, usdStage: Usd.Stage, analysis_data: dict):
        """
        Process the Usd Optimize analysis
        """

        for attribute_path in sorted(analysis_data):
            attribute: Usd.Attribute = usdStage.GetAttributeAtPath(attribute_path)
            self._AddWarning(
                message=f"Unused UV attribute",
                at=attribute,
                suggestion=Suggestion(
                    message="Remove the attribute",
                    callable=self._remove_uvs,
                    at=[attribute],
                ),
            )
