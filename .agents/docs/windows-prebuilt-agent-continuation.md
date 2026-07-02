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
