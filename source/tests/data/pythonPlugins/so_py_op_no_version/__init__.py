# SPDX-FileCopyrightText: Copyright (c) 2024-2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#


from usd_optimize.core.operation import Operation


class NoVersionPythonOperation(Operation):
    def __init__(self):
        super().__init__(
            "noVersionPythonOperation",
            "No Version Python Operation",
            "This is a Python Operation that does not implement the version property for testing purposes.",
        )

    @property
    def author(self):
        return "Usd Optimize Unit Test"

    def execute(self, args):
        return True


#####################################
# Register Usd Optimize Plugin
#####################################


def usdOptimizePluginInit():
    return NoVersionPythonOperation()
