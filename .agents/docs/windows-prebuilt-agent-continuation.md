# Windows Prebuilt Agent Continuation Notes

Read this first when resuming the Windows prebuilt `usd-optimize` bugfix work.

## Current target

The user asked to continue testing through GitHub CI and to keep documenting work in Markdown files. When a local patch needs CI validation, document it first, then commit/push it for the CI cycle.

Make the Windows prebuilt zip package usable from a clean Python process via the documented public API:

```python
from usd_optimize.bootstrap import configure_runtime
configure_runtime(package_root)

from usd_optimize.core.scripts import standalone
```

The immediate current failure is **not** a DLL failure. It is a package inclusion failure.

## Latest pushed code

Latest pushed commit when this note was written:

```text
0e66d28 fix-smoke-bootstrap-code-generation
```

Relevant commit sequence:

```text
8622eeb Add Windows CI package smoke testing
5c64c3b Use runner Python for Packman bootstrap
b7c73f1 Keep Windows package smoke running after test diagnostics
4207a69 Run Windows package smoke before wheel build
ec083b2 runtime-bootstrap-helper
0e66d28 fix-smoke-bootstrap-code-generation
```

The user has now explicitly asked to continue GitHub CI testing, so committing/pushing the current CI-test patch is allowed for this cycle.

## Detailed handoff

Full details are in:

```text
docs/windows-prebuilt-bugfix-handoff.md
```

The original larger plan is in:

```text
docs/windows-prebuilt-stability-implementation-plan.md
```

## What has been proven

Run `28580744788` passed fully and proved the generated Windows zip can work when the smoke harness manually sets up DLL directories.

Passing runtime smoke checks in that run included:

```text
pxr import
usd_optimize.core import
operation registry count > 0
usd_optimize.core.scripts.standalone import
standalone.execute_commands_from_json() on an in-memory stage
```

## Current failing CI run

Run:

```text
28582356556
```

State:

```text
completed failure
```

Important steps:

```text
Build release: success
Run tests: success/continued, with known decimate failures in logs
Upload test diagnostics: success
Build package archive: success
Smoke-test packaged runtime: failure
Upload package artifacts: success
```

Smoke failure:

```text
ModuleNotFoundError: No module named 'usd_optimize.bootstrap'
```

The smoke harness environment had:

```text
PYTHONPATH = <extracted_package>\python;<extracted_package>\usdpy
```

Therefore the package root is being used correctly, but `python/usd_optimize/bootstrap.py` is missing from the zip.

## Likely files to edit next

### Release/prebuilt zip staging

Likely file:

```text
source/core/premake5.lua
```

Current relevant staging only includes:

```lua
python_sources = "python/usd_optimize/impl/core/*.py"

usd_optimize_build.symlink_folder({
    target_dir = "python/usd_optimize/core",
    source_dir = "python/usd_optimize/core",
})
```

This does not stage:

```text
source/core/python/usd_optimize/bootstrap.py
```

The next fix should make this file appear after build as:

```text
_build/windows-x86_64/release/python/usd_optimize/bootstrap.py
```

### Wheel packaging

Likely file:

```text
tools/pyproject/pyproject.toml
```

Current `packages` include only:

```toml
{ include="usd_optimize/core" }
{ include="usd_optimize/impl" }
{ include="usd_optimize/validators" }
```

They do not obviously include root-level:

```text
usd_optimize/bootstrap.py
```

Fix the wheel path too, or the zip may pass while the wheel later misses the same module.

### Smoke preflight diagnostics

Likely file:

```text
tools/windows_prebuilt_repro/smoke_package.py
```

Improve `validate_package_root()` to explicitly check for:

```text
python/usd_optimize/bootstrap.py
python/usd_optimize/core/scripts/standalone.py
```

That would turn the current failure into an immediate package-contents error instead of five repeated subprocess import errors.

## Known unrelated failures

Full Windows Python tests show two decimate golden comparison failures:

```text
test_decimate_max_mean_error_parallel
test_decimate_max_mean_error_single_threaded
```

They are logged during CI, but the workflow currently continues so package smoke tests can still run. Do not treat these as the current package runtime blocker.

## Rerun command

After fixing packaging inclusion, rerun:

```powershell
gh workflow run "Windows Build" --repo Ahmed-Hindy/usd-optimize --ref main -f run_tests=true -f build_package=true -f usd_ver=25.11 -f python_ver=3.12
```

Then check:

```powershell
gh run list --repo Ahmed-Hindy/usd-optimize --workflow "Windows Build" --limit 3
gh api repos/Ahmed-Hindy/usd-optimize/actions/runs/<RUN_ID>/jobs --jq '.jobs[0].steps[] | [.name, .status, (.conclusion // "")] | @tsv'
```

## 2026-07-02 patch prepared for next CI run

Prepared changes:

- `source/core/premake5.lua`: targeted staging copy for `python/usd_optimize/bootstrap.py`.
- `tools/pyproject/pyproject.toml`: include `usd_optimize/bootstrap.py` in wheel package data.
- `tools/windows_prebuilt_repro/smoke_package.py`: preflight-check `python/usd_optimize/bootstrap.py` and `python/usd_optimize/core/scripts/standalone.py` before subprocess imports.
- `docs/windows-prebuilt-bugfix-handoff.md`: documented the patch and expected CI result.

Local checks passed:

```text
python -m py_compile source/core/python/usd_optimize/bootstrap.py tools/windows_prebuilt_repro/smoke_package.py
pyproject TOML parse OK
smoke preflight reports missing files and passes once placeholders exist
```

## Bootstrap package-smoke commit status

The bootstrap packaging commit was pushed and tested successfully:

```text
82e300a Package Windows runtime bootstrap module
```

## 2026-07-02 CI result for bootstrap packaging patch

Run `28585222656` tested commit:

```text
82e300a Package Windows runtime bootstrap module
```

Result: overall workflow `success` in 9m12s.

Important passing steps:

```text
Build package archive: success
Smoke-test packaged runtime: success
Upload package artifacts: success
```

Smoke evidence:

```text
pxr import and in-memory stage creation succeeded
usd_optimize.core import succeeded
operation registry contains 47 operations
public standalone API import succeeded
standalone JSON execution succeeded
```

The zip runtime blocker is fixed.

## Current next blocker — Python wheel staging

The same run still had a non-blocking `Build Python wheel` failure:

```text
ValueError: _build/pyproject/omni/scene/optimizer does not contain any element
IndexError: list index out of range in tools/repoman/py_package.py after no wheel was produced
```

Root cause: `tools/repoman/py_package.py` stages only `_build/<platform>/<config>/python/usd_optimize` into `_build/pyproject`, while `tools/pyproject/pyproject.toml` declares the deprecated `omni/scene/optimizer` compatibility shim as a package. The built package tree already has `python/omni/scene/optimizer`; the wheel staging script must copy it.

Patch prepared:

- `tools/repoman/py_package.py`: copy `_build/<platform>/<config>/python/omni` into `_build/pyproject/omni` when the source exists.

Local check passed:

```text
python -m py_compile tools/repoman/py_package.py
```

Next CI expectation: package smoke remains green, and `Build Python wheel` should no longer fail on a missing `omni/scene/optimizer` package tree.

## 2026-07-02 CI result for wheel staging patch

Run `28586207717` tested commit `5f76642 wheel-staging-fix`.

Result: overall workflow `success` in 9m19s.

Important passing steps:

```text
Build package archive: success
Smoke-test packaged runtime: success
Build Python wheel: success
Upload package artifacts: success
```

The wheel staging blocker is fixed. The only remaining workflow annotation is the known non-blocking full test failure from `test.python.bat`.

## Current patch — external OpenUSD fixture smoke test

Prepared changes:

- Added `source/tests/data/external/openusd_helloworld.usda` from OpenUSD `extras/usd/tutorials/authoringProperties/HelloWorld.usda` on the `release` branch.
- Added `source/tests/data/external/README.md` with source, branch, license, and test-purpose notes.
- Added optional `--external-fixture-usd` support to `tools/windows_prebuilt_repro/smoke_package.py`.
- Updated `.github/workflows/windows-build.yml` so package smoke passes the OpenUSD fixture path in CI.

Expected next CI result: `Smoke-test packaged runtime` should include and pass an `external_fixture_open` check that opens the file-backed fixture and asserts `/hello/world` exists.

## 2026-07-02 CI result for external OpenUSD fixture

Run `28590020858` tested commit:

```text
1ddf8cb fixture-smoke
```

Result: overall workflow `success` in 9m10s.

Relevant smoke log evidence:

```text
PASSED: pxr_import
PASSED: core_import
PASSED: operation_registry
PASSED: standalone_import
PASSED: standalone_execute
=== external_fixture_open ===
external USD fixture opened successfully: D:\a\usd-optimize\usd-optimize\source\tests\data\external\openusd_helloworld.usda
PASSED: external_fixture_open
```

This proves the Windows prebuilt package can open a real file-backed USD fixture from the repo, not only an in-memory stage.

## Current patch — decimate golden comparison cleanup

Current remaining CI annotation after run `28590020858`:

```text
test_decimate_max_mean_error_parallel: failed golden file comparison
test_decimate_max_mean_error_single_threaded: failed golden file comparison
```

Both failures reported the expected decimated mesh counts: `VertexCount: 550000 -> 2954` and `FaceCount: 539055 -> 4567`.

Root cause hypothesis: the test already had a semantic mesh comparison fallback for `.usdc` golden comparisons, but these two tests write `.usda` result files. Windows/USD 25.11 appears to serialize equivalent decimated USDA differently enough to fail raw text comparison.

Prepared patch:

- Rename `_compare_decimate_usdc_stages()` to `_compare_decimate_stages()`.
- Keep raw file comparison first.
- For decimate golden files, fall back to semantic comparison of prim paths, type names, mesh points, face counts, face indices, and normals when raw text comparison fails.

Local check passed:

```text
py -3 -m py_compile source/tests/test.python/test_operation_decimate_meshes.py
```

## 2026-07-02 CI result for decimate comparison patch

Run `28594618988` tested commit:

```text
8e4e9ea decimate-semantic-golden-compare
```

Result: overall workflow `success` in 8m49s.

Important log evidence:

```text
Ran 591 tests in 69.216s
OK (skipped=1)
[ ok ] test process passed.
[   ok   ] [  70.7s]            test.python.bat
PASSED: external_fixture_open
Packaged wheel installed to _build/packages/usd_optimize-1.0.4-cp312-cp312-win_amd64.whl
```

The previous `Process completed with exit code 2` workflow annotation is gone. The only remaining annotation is GitHub's Node.js 20 deprecation warning for upstream GitHub actions, not a repo test/package failure.

## Current patch — external USD asset smoke set on CI

Goal: move broader USD asset testing into GitHub CI without committing larger external assets into the repository.

Prepared changes:

- `tools/windows_prebuilt_repro/external_usd_assets.json`: manifest of ten public OpenUSD tutorial files from the Pixar OpenUSD `release` branch, with raw URLs, relative cache paths, expected prims, SHA-256 hashes, and `"smoke": false` for three Ball/Table sibling dependencies.
- `tools/windows_prebuilt_repro/download_external_assets.py`: downloads assets into `.cache/usd-assets` and verifies SHA-256 before smoke tests use them.
- `tools/windows_prebuilt_repro/smoke_package.py`: accepts `--external-asset-manifest` and `--external-assets-dir`; opens every primary smoke asset through the packaged runtime; verifies expected prims; defines and deletes a temporary in-memory prim via `deletePrims`.
- `.github/workflows/windows-build.yml`: adds `USD_ASSET_CACHE_DIR`, restores an `actions/cache` entry keyed by the manifest hash, downloads assets before package smoke, and passes the manifest/cache directory to the smoke harness.

Asset source and license:

- Source repository: `https://github.com/PixarAnimationStudios/OpenUSD`
- Source branch: `release`
- License reference: OpenUSD `LICENSE.txt`, Tomorrow Open Source Technology License 1.0.

Local checks passed:

```text
py -3 -m py_compile tools/windows_prebuilt_repro/download_external_assets.py tools/windows_prebuilt_repro/smoke_package.py
manifest ok: 7
ast ok
```

CI result after dispatch:

Run `28601992947` tested commit `e1f8fca external-usd-asset-ci-smoke` and passed overall in 10m56s. It proved the external asset smoke flow worked, but Ball/Table emitted unresolved-reference warnings for sibling files.

Follow-up commit `ab722d2 complete-external-usd-asset-dependencies` added three dependency files to the manifest and marked them `"smoke": false`, so they are downloaded/hash-verified but not opened as standalone smoke roots.

Run `28603073890` tested commit `ab722d2` and passed overall in 9m44s.

Important final log evidence:

```text
Cache restored from key: external-usd-assets-59ab2e004997bc3da6b0201b81c366671ef94a4a55f96b9bdfe987fea094bfb2
External USD assets ready: 10
PASSED: external_fixture_open
external asset smoke passed: authoring_properties_hello_world (2 prims)
external asset smoke passed: converting_layer_formats_sphere (1 prims)
external asset smoke passed: simple_shading (6 prims)
external asset smoke passed: traversing_stage_hello_world_dependency (2 prims)
external asset smoke passed: traversing_stage_reference_example (4 prims)
external asset smoke passed: end_to_end_ball_asset (7 prims)
external asset smoke passed: end_to_end_table_asset (7 prims)
external asset manifest smoke passed for 7 assets
PASSED: external_asset_manifest_smoke
Packaged wheel installed to _build/packages/usd_optimize-1.0.4-cp312-cp312-win_amd64.whl
```

The asset-smoke section no longer reports unresolved Ball/Table reference warnings. The only workflow annotation remains GitHub's Node.js 20 deprecation warning for upstream GitHub actions, not a repo failure.

## 2026-07-03 current patch — safe operation matrix

Goal: move from open-only asset smoke to conservative real operation checks on the downloaded external USD assets.

Prepared changes:

- `tools/windows_prebuilt_repro/safe_operation_matrix.json`: defines three conservative operations: `printStats`, `computeExtents`, and `optimizePrimvars` in indexing/simplify mode with `removeIfBound=false`.
- `tools/windows_prebuilt_repro/smoke_package.py`: adds `--safe-operation-matrix`; for each primary external smoke asset, runs each operation through `standalone.execute_commands_from_json()`, exports a temporary sibling `.usda`, reopens it, verifies expected prims, and checks prim count preservation.
- `.github/workflows/windows-build.yml`: passes the matrix into the packaged runtime smoke step.
- `docs/windows-prebuilt-bugfix-handoff.md`: documents the patch, local checks, and expected CI outcome.

Local checks passed:

```text
python -m py_compile tools/windows_prebuilt_repro/smoke_package.py
safe_operation_matrix.json parsed with 3 operations
generated operation matrix subprocess code compiles
line length check passed for smoke_package.py
```

Run `28664838966` tested commit `94f22c3 Add safe operation package smoke matrix`. Build, full tests, package archive, external asset download, and previous package smoke checks passed, but the new matrix failed immediately on `printStats`:

```text
[ERROR] printStats: Failed to set arguments, cannot execute operation.
AssertionError: operation matrix command failed: print_stats on authoring_properties_hello_world
```

Root cause: the matrix passed `time: false`, but `printStats` expects its `time` argument as a numeric time value when provided. Patch prepared: call `printStats` with default arguments only.

Follow-up commit `eaad6be Fix printStats package smoke arguments` changed the matrix to call `printStats` with defaults only.

Run `28665543591` tested commit `eaad6be` and passed overall in 9m16s.

Important final evidence:

```text
Build release: success
Run tests: success
Build package archive: success
Download external USD assets: success
Smoke-test packaged runtime: success
Build Python wheel: success
external asset operation matrix smoke passed for 21 operation runs
PASSED: external_asset_operation_matrix_smoke
Packaged wheel installed to _build/packages/usd_optimize-1.0.4-cp312-cp312-win_amd64.whl
```

Current next target: expand operation coverage carefully, one small operation family at a time. Do not add destructive/default-unsafe operations to the matrix without operation-specific expected-output checks.
