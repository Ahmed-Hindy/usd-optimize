# SPDX-FileCopyrightText: Copyright (c) 2024-2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#


from usd_optimize.core.operation import Operation


class BadVersion2PythonOperation(Operation):
    def __init__(self):
        super().__init__(
            "badVersion2PythonOperation",
            "Bad Version 2 Python Operation",
            "This is a Python Operation that returns a tuple with only 2 elements from the version property for testing purposes.",
        )

    @property
    def author(self):
        return "Usd Optimize Unit Test"

    @property
    def version(self):
        return (1, 2)

    def execute(self, args):
        return True


#####################################
# Register Usd Optimize Plugin
#####################################


def usdOptimizePluginInit():
    return BadVersion2PythonOperation()
