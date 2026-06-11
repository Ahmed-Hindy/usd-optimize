# SPDX-FileCopyrightText: Copyright (c) 2024-2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#


from usd_optimize.core.operation import Operation


class DisplayNameErrorPythonOperation(Operation):
    def __init__(self):
        super().__init__(
            "displayNameErrorPythonOperation",
            "Display Name Error Python Operation",
            "This is a Python Operation that raises an error in the display_name property for testing purposes.",
        )

    @property
    def display_name(self):
        raise RuntimeError("Display Name Error")

    @property
    def author(self):
        return "Usd Optimize Unit Test"

    @property
    def version(self):
        return (1, 2, 3)

    def execute(self, args):
        return True


#####################################
# Register Usd Optimize Plugin
#####################################


def usdOptimizePluginInit():
    return DisplayNameErrorPythonOperation()
