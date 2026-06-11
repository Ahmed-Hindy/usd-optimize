# SPDX-FileCopyrightText: Copyright (c) 2024-2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#

from pxr import Usd, UsdGeom, UsdUtils
from usd_optimize.core import ExecutionContext, UsdOptimizeCore
from usd_optimize.core.operation import Operation


class DeleteHiddenPrimsOperation(Operation):
    def __init__(self):
        super().__init__("deleteHiddenPrims", "Delete Hidden Prims", "Deletes all prims that are constantly hidden.")

    @property
    def author(self):
        return "Usd Optimize (Internal)"

    @property
    def version(self):
        return (1, 0, 0)

    @property
    def visible(self):
        return False

    def execute(self, _args):
        stage = self.get_usd_stage()
        hidden_prim_paths = []

        # Does not include instance proxies
        it = iter(Usd.PrimRange.Stage(stage, Usd.PrimIsLoaded & ~Usd.PrimIsAbstract))

        for prim in Usd.PrimRange(stage.GetPseudoRoot()):
            imageable = UsdGeom.Imageable(prim)
            if imageable:
                vis_attr = imageable.GetVisibilityAttr()
                if vis_attr.Get() == UsdGeom.Tokens.invisible:
                    it.PruneChildren()
                    hidden_prim_paths.append(str(prim.GetPath()))

        args = {"primPaths": hidden_prim_paths}

        # execute the deletePrims operation
        context = ExecutionContext()
        context.usdStageId = UsdUtils.StageCache.Get().GetId(stage).ToLongInt()
        UsdOptimizeCore.getInstance().executeOperation("deletePrims", context, args)

        return True


#####################################
# Register Usd Optimize Plugin
#####################################


def usdOptimizePluginInit():
    return DeleteHiddenPrimsOperation()
