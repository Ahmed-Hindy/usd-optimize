# SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#


# expose the implementation as the API
from usd_optimize.impl.core import *

# Force the C++ core's lazy plugin load (which ``PyImport_Import``s the
# Python-implemented operations under
# ``usd_optimize.libs/operations/<name>/``) to happen on the
# importing thread, before any caller can dispatch ``executeOperation`` from
# a worker thread.
#
# The binding's ``getInstance`` wrapper guards ``loadPlugins`` with
# ``std::call_once``, but the imports inside ``loadPlugins`` release the GIL
# during file I/O, which lets other threads enter Python's import machinery
# for the same modules. Combined with CPython's per-module import lock
# that's a textbook GIL/import-lock deadlock — observed when
# ``usd-validation-nvidia``'s ``AsyncComplianceCheckerRunner`` dispatched
# ``CheckStage`` rules to a multi-worker ``ThreadPoolExecutor``.
#
# Triggering ``getInstance()`` here serialises the plugin imports on the
# single thread that's importing this package (Python's import machinery
# already serialises this), so by the time any subsequent caller (worker
# thread or otherwise) reaches the binding the singleton is fully
# initialised and ``call_once`` short-circuits.
UsdOptimizeCore.getInstance()  # noqa: F405


# Deprecated class-name alias. Defined via module-level __getattr__ so that
# the warning fires only on actual access (i.e., `from usd_optimize.core
# import SceneOptimizerCore` or `usd_optimize.core.SceneOptimizerCore`) and
# not for every `import usd_optimize.core`.
def __getattr__(name):
    if name == "SceneOptimizerCore":
        import warnings

        warnings.warn(
            "`SceneOptimizerCore` is deprecated; use `UsdOptimizeCore` instead.",
            DeprecationWarning,
            stacklevel=2,
        )
        return UsdOptimizeCore  # noqa: F405
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
