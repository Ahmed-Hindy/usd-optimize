# SPDX-FileCopyrightText: Copyright (c) 2024-2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#


from usd_optimize.core.operation import Operation


class InitFuncNonePythonOperation(Operation):
    def __init__(self):
        super().__init__(
            "initFuncNonePythonOperation",
            "Init Func None Python Operation",
            "This is a Python Operation that returns None from the init function for testing purposes.",
        )

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
    return None
