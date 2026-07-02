# SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#

import json
import unittest

from pxr import Usd, UsdGeom
from usd_optimize.core.scripts import standalone


class TestStandalonePublicApi(unittest.TestCase):
    def test_public_standalone_import_and_execute_json(self):
        """The documented standalone API should import and execute JSON commands."""
        stage = Usd.Stage.CreateInMemory()
        UsdGeom.Xform.Define(stage, "/World")
        UsdGeom.Cube.Define(stage, "/World/keep")
        UsdGeom.Cube.Define(stage, "/World/delete_me")

        operations_json = json.dumps(
            [
                {"operation": "executionContext", "verbose": False},
                {"operation": "deletePrims", "primPaths": ["/World/delete_me"]},
            ]
        )

        self.assertTrue(standalone.execute_commands_from_json(stage, operations_json))
        self.assertTrue(stage.GetPrimAtPath("/World/keep"))
        self.assertFalse(stage.GetPrimAtPath("/World/delete_me"))
