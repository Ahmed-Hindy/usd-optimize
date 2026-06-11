# SPDX-FileCopyrightText: Copyright (c) 2024-2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#


from usd_optimize.core.operation import Operation


class VisibleErrorPythonOperation(Operation):
    def __init__(self):
        super().__init__(
            "visibleErrorPythonOperation",
            "Visible Error Python Operation",
            "This is a Python Operation that raises an error in the visible property for testing purposes.",
        )

    @property
    def author(self):
        return "Usd Optimize Unit Test"

    @property
    def version(self):
        return (1, 2, 3)

    @property
    def visible(self):
        raise RuntimeError("visible error")

    def execute(self, args):
        return True


#####################################
# Register Usd Optimize Plugin
#####################################


def usdOptimizePluginInit():
    return VisibleErrorPythonOperation()
