# SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#
"""Deprecated compatibility alias for the ``usd_optimize`` package.

The project was renamed from *Scene Optimizer* to *Usd Optimize*. Every
``omni.scene.optimizer.<name>`` import is transparently redirected to
``usd_optimize.<name>`` via a ``sys.meta_path`` finder installed below, so
``import omni.scene.optimizer.core`` keeps working — the returned module is
the *same object* as ``usd_optimize.core``.

A single ``DeprecationWarning`` fires the first time anything under this
namespace is imported. Update callers to import from ``usd_optimize``
directly; this shim will be removed in a future release.
"""

import sys
import warnings
from importlib import import_module
from importlib.abc import Loader, MetaPathFinder
from importlib.machinery import ModuleSpec

_OLD_PREFIX = "omni.scene.optimizer"
_NEW_PREFIX = "usd_optimize"


class _AliasLoader(Loader):
    """Loader that returns an already-imported target module."""

    def __init__(self, target_name: str) -> None:
        self._target_name = target_name

    def create_module(self, spec):
        # Import (or fetch from cache) the real module and use it as the
        # module object for the aliased name. The import system will set
        # ``sys.modules[spec.name] = <returned>`` after exec_module runs.
        return import_module(self._target_name)

    def exec_module(self, module) -> None:
        # Nothing to execute — the target module was fully initialised by
        # ``import_module`` inside ``create_module``.
        pass


class _AliasFinder(MetaPathFinder):
    """Map ``omni.scene.optimizer.<sub>`` lookups to ``usd_optimize.<sub>``."""

    def find_spec(self, fullname, path=None, target=None):
        if not fullname.startswith(_OLD_PREFIX + "."):
            return None
        target_name = _NEW_PREFIX + fullname[len(_OLD_PREFIX) :]
        return ModuleSpec(fullname, _AliasLoader(target_name))


# Install the finder at the head of sys.meta_path exactly once. It must run
# *before* the default ``PathFinder``: once ``omni.scene.optimizer.impl`` is
# aliased to ``usd_optimize.impl``, that target's ``__path__`` would otherwise
# let ``PathFinder`` resolve ``omni.scene.optimizer.impl.core`` to a fresh
# module instead of the cached ``usd_optimize.impl.core`` — breaking identity.
if not any(isinstance(f, _AliasFinder) for f in sys.meta_path):
    sys.meta_path.insert(0, _AliasFinder())

warnings.warn(
    "`omni.scene.optimizer` is deprecated; import from `usd_optimize` instead.",
    DeprecationWarning,
    stacklevel=2,
)
