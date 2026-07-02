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

## Current local commit / push status

Local commit created:

```text
2467a13 Package Windows runtime bootstrap module
```

The DevSpace tool environment allowed staging and committing but blocked `git push` / `git push origin main`. To continue GitHub CI testing, push this commit first:

```powershell
git push origin main
```

Then dispatch the Windows workflow from the pushed `main` branch.

## Expected next green state

The next good CI run should show:

```text
Build package archive: success
Smoke-test packaged runtime: success
Upload package artifacts: success
```

Only after that should you investigate the next runtime failure, if one appears.
