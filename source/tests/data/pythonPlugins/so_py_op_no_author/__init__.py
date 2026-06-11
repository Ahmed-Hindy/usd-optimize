# SPDX-FileCopyrightText: Copyright (c) 2024-2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#


from usd_optimize.core.operation import Operation


class NoAuthorPythonOperation(Operation):
    def __init__(self):
        super().__init__(
            "noAuthorPythonOperation",
            "No Author Python Operation",
            "This is a Python Operation that does not implement the author property for testing purposes.",
        )

    @property
    def version(self):
        return (1, 2, 3)

    def execute(self, args):
        return True


#####################################
# Register Usd Optimize Plugin
#####################################


def usdOptimizePluginInit():
    return NoAuthorPythonOperation()
