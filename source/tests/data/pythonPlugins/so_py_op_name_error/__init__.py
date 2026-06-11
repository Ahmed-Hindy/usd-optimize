# SPDX-FileCopyrightText: Copyright (c) 2024-2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#


from usd_optimize.core.operation import Operation


class NameErrorPythonOperation(Operation):
    def __init__(self):
        super().__init__(
            "nameErrorPythonOperation",
            "Name Error Python Operation",
            "This is a Python Operation that raises an error in the name property for testing purposes.",
        )

    @property
    def name(self):
        raise RuntimeError("Name Error")

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
    return NameErrorPythonOperation()
