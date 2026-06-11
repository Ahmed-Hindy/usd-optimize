# SPDX-FileCopyrightText: Copyright (c) 2025-2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#
from typing import List

from pxr import Usd
from usd_optimize.core import analysis
from usd_validation_nvidia import Suggestion, capabilities, register_requirements

from .base_usd_optimize_checker import BaseUsdOptimizeChecker


@register_requirements(capabilities.HierarchyRequirements.HI_012)
class EmptyLeafChecker(BaseUsdOptimizeChecker):
    """
    Check a stage for redundant leaf primitives (Scopes, Xforms).
    """

    OPERATION_NAME: str = "pruneLeaves"
    OPERATION_ARGS: dict = {"filterInactive": True}

    @classmethod
    def _remove_leaves(cls, usdStage: Usd.Stage, _: Usd.Stage) -> None:
        """
        Prune leaf prims via Usd Optimize
        """

        # Configure operation
        operations: List[analysis.OperationConfig] = [
            analysis.OperationConfig(cls.OPERATION_NAME, args=cls.OPERATION_ARGS),
        ]

        # Execute the optimization via Usd Optimize.
        analysis.optimize(usdStage, operations)

    def _CheckStage(self, usdStage: Usd.Stage, analysis_data: dict):
        """
        Process the Usd Optimize analysis of empty leaves and log warnings/suggestions.
        """

        leaves: int = len(analysis_data)
        suffix: str = "" if leaves == 1 else "s"
        message: str = f"Stage contains {leaves} empty leaf primitive{suffix}"

        self._AddWarning(
            message=message,
            at=usdStage,
            suggestion=Suggestion(
                message="Remove empty leaf primitives with Usd Optimize", callable=self._remove_leaves, at=None
            ),
        )
