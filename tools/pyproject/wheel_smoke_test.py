# SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#

"""Smoke test for an installed ``usd-optimize`` wheel.

Run with the Python interpreter of the virtual environment the wheel was
installed into (see ``test_wheel.sh`` / ``test_wheel.bat``). It exercises the
parts of the package most likely to break in a packaged build:

* importing ``usd_optimize.core`` (loads the pybind extension + its bundled
  shared libraries),
* the lazy C++ plugin load triggered on import (``dlopen`` of every operation
  plugin under ``usd_optimize.libs/operations`` — the step that surfaces
  missing/renamed ``libusd_optimize.core.so`` style errors),
* running a real operation end-to-end against an in-memory USD stage.

Exits non-zero with a readable message on any failure.
"""

import sys


def main():
    # Importing the package triggers UsdOptimizeCore.getInstance(), which
    # dlopens every operation plugin. A packaging/RPATH regression fails here.
    from pxr import Usd, UsdGeom
    from usd_optimize.core import ExecutionContext, UsdOptimizeCore

    core = UsdOptimizeCore.getInstance()

    ops = core.getOperations()
    if "countVertices" not in ops:
        raise AssertionError(
            f"expected the 'countVertices' operation to be registered; "
            f"got {len(ops)} operations: {sorted(ops)[:10]}..."
        )
    print(f"[smoke] import OK — {len(ops)} operations registered")

    # Build a trivial stage: one quad mesh (4 vertices).
    stage = Usd.Stage.CreateInMemory()
    mesh = UsdGeom.Mesh.Define(stage, "/World/Mesh")
    mesh.CreatePointsAttr([(0, 0, 0), (1, 0, 0), (1, 1, 0), (0, 1, 0)])
    mesh.CreateFaceVertexCountsAttr([4])
    mesh.CreateFaceVertexIndicesAttr([0, 1, 2, 3])

    context = ExecutionContext()
    context.set_stage(stage)
    context.analysisMode = 1

    # Run countVertices in analysis mode; thresholds chosen so the 4-vertex
    # quad lands in the "high" bucket, proving the plugin actually executed.
    result = core.executeOperation(
        "countVertices", context, {"high": 4, "veryHigh": 100, "extreme": 1000}
    )
    success, error, extra = result[0], result[1], result[2]
    if not success:
        raise AssertionError(f"countVertices failed: {error}")
    if not isinstance(extra, dict) or "analysis" not in extra:
        raise AssertionError(f"countVertices returned no analysis payload: {extra!r}")
    print(f"[smoke] countVertices executed — analysis buckets: {list(extra['analysis'])}")

    print("[smoke] PASS")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:  # noqa: BLE001 - top-level smoke-test reporter
        print(f"[smoke] FAIL: {type(exc).__name__}: {exc}", file=sys.stderr)
        sys.exit(1)
