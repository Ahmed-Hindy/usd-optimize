# SPDX-FileCopyrightText: Copyright (c) 2025-2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#

from typing import List

from pxr import Usd, UsdGeom
from usd_optimize.core import analysis
from usd_validation_nvidia import Suggestion, capabilities, register_requirements

from .base_usd_optimize_checker import BaseUsdOptimizeChecker

# Usd Optimize mode to force index a primvar
MODE_INDEX_FORCED = 2


@register_requirements(capabilities.GeometryRequirements.VG_009, override=True)
class IndexedPrimvarChecker(BaseUsdOptimizeChecker):
    """
    For Primvars with non-constant values of interpolation, it is often the case that the same value is repeated many
    times in the array.

    An indexed primvar can be used in such cases to optimize for data storage if the primvar's interpolation is
    non-constant (i.e. uniform, varying, face varying or vertex).

    This Checker also looks for indexed primvars whose indices are out of bounds, or use a non-constant interpolation
    but do not contain array-type data.
    """

    OPERATION_NAME: str = "optimizePrimvars"

    @classmethod
    def _index_primvar(cls, usdStage: Usd.Stage, attribute: Usd.Attribute) -> None:
        """
        Index a primvar with Usd Optimize.
        """

        # Configure optimize primvars with this specific prim path and primvar name.
        # TODO: It would be nice to be able to bulk apply these. If not, we can at
        #       least add a mode to Usd Optimize to target a specific attribute path
        operations: List[analysis.OperationConfig] = [
            analysis.OperationConfig(
                cls.OPERATION_NAME, args={"primvarPaths": [str(attribute.GetPath())], "mode": MODE_INDEX_FORCED}
            ),
        ]

        # Execute the optimization via Usd Optimize.
        analysis.optimize(usdStage, operations)

    def _CheckStage(self, usdStage: Usd.Stage, analysis_data: dict):
        """
        Process the Usd Optimize analysis of primvar issues and log warnings/suggestions.
        """

        # Primvars with repeated values that could be indexed
        indexable: List[str] = analysis_data["indexable"]
        for path in sorted(indexable):
            primvar = UsdGeom.Primvar(usdStage.GetAttributeAtPath(path))
            self._AddWarning(
                # requirement=cap.GeometryRequirements.VG_009,
                message=f"{primvar.GetName()} contains repeated values that can be indexed.",
                at=primvar.GetAttr(),
                suggestion=Suggestion(
                    message="Index the primvar with Usd Optimize",
                    callable=self._index_primvar,
                    at=[primvar.GetAttr()],
                ),
            )

        # Primvars with indices that are out of bounds
        out_of_bounds: List[str] = analysis_data["outOfBounds"]
        for path in sorted(out_of_bounds):
            primvar = UsdGeom.Primvar(usdStage.GetAttributeAtPath(path))
            self._AddError(
                # requirement=cap.GeometryRequirements.VG_009,
                message="Primvar indices out of bounds",
                at=primvar.GetAttr(),
            )

        # Non-constant interpolated primvars that are not array typed
        non_array: List[str] = analysis_data["nonArray"]
        for path in sorted(non_array):
            primvar = UsdGeom.Primvar(usdStage.GetAttributeAtPath(path))
            self._AddError(
                # requirement=cap.GeometryRequirements.VG_009,
                message="Primvar is not of array type.",
                at=primvar.GetAttr(),
            )
