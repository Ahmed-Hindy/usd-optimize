# SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#
"""Smoke test for the `omni.scene.optimizer` → `usd_optimize` compat shim.

The shim is a `sys.meta_path` finder that rewrites the old import path
transparently. These checks guard against (1) the shim package failing to
ship, (2) the finder not registering, and (3) the aliased modules drifting
from the real ones.
"""

import importlib
import sys
import unittest
import warnings


class TestCompatAlias(unittest.TestCase):

    def _fresh_import(self, name):
        """Re-import `name` after evicting it (and its parent chain) from
        sys.modules so the meta-path finder runs again."""
        # Drop only the omni.scene.optimizer.* chain; the real usd_optimize
        # modules can stay cached.
        for cached in [
            k for k in list(sys.modules) if k == "omni.scene.optimizer" or k.startswith("omni.scene.optimizer.")
        ]:
            del sys.modules[cached]
        return importlib.import_module(name)

    def test_core_alias_identity(self):
        """`omni.scene.optimizer.core` is the same module object as `usd_optimize.core`."""
        import usd_optimize.core as real

        alias = self._fresh_import("omni.scene.optimizer.core")
        self.assertIs(alias, real)

    def test_from_import_class(self):
        """`from omni.scene.optimizer.core import UsdOptimizeCore` returns the real class."""
        self._fresh_import("omni.scene.optimizer.core")
        from omni.scene.optimizer.core import UsdOptimizeCore as ViaAlias
        from usd_optimize.core import UsdOptimizeCore as ViaReal

        self.assertIs(ViaAlias, ViaReal)

    def test_impl_core_alias(self):
        import usd_optimize.impl.core as real

        alias = self._fresh_import("omni.scene.optimizer.impl.core")
        self.assertIs(alias, real)

    def test_deprecation_warning_emitted(self):
        """First import through the shim emits a DeprecationWarning."""
        # Clear the omni.scene.optimizer chain so the parent __init__ re-executes.
        for cached in [
            k for k in list(sys.modules) if k == "omni.scene.optimizer" or k.startswith("omni.scene.optimizer.")
        ]:
            del sys.modules[cached]
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            importlib.import_module("omni.scene.optimizer.core")
        deprecations = [w for w in caught if issubclass(w.category, DeprecationWarning)]
        self.assertTrue(deprecations, "expected at least one DeprecationWarning")
        self.assertIn("usd_optimize", str(deprecations[0].message))

    def test_scene_optimizer_core_class_alias(self):
        """`SceneOptimizerCore` resolves to `UsdOptimizeCore` on both `usd_optimize.core`
        and `usd_optimize.impl.core`, and on the deprecated `omni.scene.optimizer.*`
        proxies — all four lookups return the same class."""
        import usd_optimize.core
        import usd_optimize.impl.core

        self._fresh_import("omni.scene.optimizer.core")
        self._fresh_import("omni.scene.optimizer.impl.core")

        canonical = usd_optimize.core.UsdOptimizeCore
        # Silence the per-access DeprecationWarning while we collect the four refs.
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", DeprecationWarning)
            from omni.scene.optimizer.core import SceneOptimizerCore as via_omni_core
            from omni.scene.optimizer.impl.core import SceneOptimizerCore as via_omni_impl_core
            from usd_optimize.core import SceneOptimizerCore as via_core
            from usd_optimize.impl.core import SceneOptimizerCore as via_impl_core

        for ref in (via_core, via_impl_core, via_omni_core, via_omni_impl_core):
            self.assertIs(ref, canonical)

    def test_scene_optimizer_core_emits_warning(self):
        """Accessing `SceneOptimizerCore` triggers a DeprecationWarning that mentions
        the new name."""
        import usd_optimize.core  # noqa: F401

        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            _ = usd_optimize.core.SceneOptimizerCore
        deprecations = [w for w in caught if issubclass(w.category, DeprecationWarning)]
        self.assertTrue(deprecations, "expected DeprecationWarning on access")
        msg = str(deprecations[0].message)
        self.assertIn("SceneOptimizerCore", msg)
        self.assertIn("UsdOptimizeCore", msg)


if __name__ == "__main__":
    unittest.main()
