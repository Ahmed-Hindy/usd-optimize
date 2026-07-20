# Windows Release Package Smoke Test

`tools/release_smoke/windows_package_smoke.py` tests an extracted Windows
CPython 3.12 package in separate processes. It is designed to distinguish a
native package-loader crash from a normal operation failure.

It verifies:

1. `pxr` can create an in-memory stage.
2. `usd_optimize.core` loads and registers `findOverlappingMeshes`.
3. `UsdOptimizeCore.executeConfig()` can execute `deletePrims`.
4. `findOverlappingMeshes` CPU analysis returns eight known overlap findings.
5. The packaged `usdOptimize.exe` can run the same overlap analysis.
6. Optionally, 42 conservative operations run against seven checksum-pinned
   OpenUSD tutorial assets. Each output is reopened and checked for expected
   prims and unchanged prim counts.

The fixture is intentionally source-controlled but is only input data; Python,
OpenUSD, DLLs, plugins, and the CLI under test all come from the package.

## Run locally

Use CPython 3.12, matching the package ABI:

```powershell
py -3.12 tools/release_smoke/windows_package_smoke.py `
  --package-archive C:\path\to\usd_optimize_usd_25.11_py_3.12@<version>.windows-x86_64.release.zip `
  --overlap-fixture-usd source/tests/data/sphere_clashes_frame.usda
```

For an already extracted package, replace `--package-archive ...` with
`--package-root C:\path\to\release-runtime`.

To run the optional external matrix locally, first populate a cache and pass
the three external-matrix arguments:

```powershell
py -3.12 tools/release_smoke/download_external_assets.py `
  --manifest tools/release_smoke/external_usd_assets.json `
  --assets-dir .cache/release-smoke-assets
```

## Run in GitHub Actions

Dispatch **Windows release package smoke** and provide the upstream release
tag plus an asset pattern that matches exactly one archive. The default targets
the OpenUSD 25.11 / CPython 3.12 Windows package from
`NVIDIA-Omniverse/usd-optimize`.

The external matrix is enabled by default for a manual workflow dispatch. Turn
it off when only the focused native-loader and overlap regression is needed.

The workflow uploads the full smoke log, including a native process exit code
such as `3221225477` (`0xC0000005`) if a loader crash recurs.
