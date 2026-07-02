# Windows Prebuilt Stability Implementation Plan

## Purpose

This document is the implementation plan for making the Windows prebuilt `usd-optimize` package reliable enough to use as a standalone optimization tool on production USD assets.

The immediate trigger is a set of Windows failures observed while testing the public/prebuilt package against real Kitbash-style USD assets. The failures are not just user-environment mistakes. They point to a combination of Windows packaging gaps, fragile import-time plugin initialization, weak diagnostics, and shutdown/lifetime problems.

The goal is not to add a wrapper workaround around a broken runtime. The goal is to make the upstream package behave predictably when extracted into a clean Windows environment and used through its documented Python API.

## Big Picture

Usd Optimize has three distinct runtime surfaces that must agree with each other:

1. **The C++ core and operation plugin system**
   - Loads native operation DLLs.
   - Owns the operation registry.
   - Executes operations against USD stages.

2. **The Python binding/API layer**
   - Exposes `ExecutionContext`, `UsdOptimizeCore`, operation metadata, and operation execution.
   - Imports Python-implemented operations.
   - Currently triggers plugin loading through `UsdOptimizeCore.getInstance()` during `import usd_optimize.core`.

3. **The distributed Windows prebuilt package**
   - Must contain all runtime DLLs required by USD, MaterialX, Python bindings, and operation plugins.
   - Must document the exact `PYTHONPATH`, `PATH`, and DLL search requirements.
   - Must include the Python API modules referenced by the docs and smoke tests.

The current failure mode suggests these surfaces are out of sync. A user can follow the documentation and still hit missing DLLs, missing Python modules, operation registry crashes, noisy MaterialX failures, or shutdown access violations.

This plan fixes that by first creating reliable reproduction and diagnostics, then hardening runtime loading, then correcting the package/docs/API mismatch, and finally adding CI coverage so the same class of failure does not return.

## Non-goals

- Do not optimize a specific asset yet. The priority is package/runtime correctness.
- Do not hide native crashes with only wrapper-side `os._exit(0)` behavior.
- Do not remove existing plugin initialization behavior without replacing the thread-safety reason it was originally added for.
- Do not make Linux-only assumptions about shared library resolution, unload order, or file replacement semantics.
- Do not commit changes until explicitly requested.

## Current Findings to Preserve

The prior investigation produced several important observations that should drive the implementation:

- Windows DLL resolution likely needs `lib`, `extraLibs`, and possibly `lib/operations` to be handled explicitly.
- Importing `usd_optimize.core` currently initializes the core singleton and loads plugins as an import side effect.
- Python operation plugins import `usd_optimize.core`, which can interact badly with eager plugin loading.
- Successful operation execution followed by a crash during process shutdown points toward `Py_AtExit`, plugin unload, singleton lifetime, or Python finalization ordering.
- The documented `usd_optimize.core.scripts.standalone` API must exist in the published package if docs and smoke tests mention it.
- The Windows prebuilt package appears to load `usd_usdMtlx.dll` without all required MaterialX DLLs available.
- Operation DLL names are not always the same as operation registry keys, so tools must query metadata rather than infer names from filenames.
- Some operations are not safely runnable with default arguments and need metadata to say whether they require parameters, are analysis-only, or are destructive.

## Implementation Strategy

Work in small, verifiable layers. Each layer must leave behind a test or diagnostic that proves the fix and guards against regressions.

Recommended order:

1. Reproduce and document failures in a clean Windows environment.
2. Add a `doctor`/diagnostic path before changing behavior.
3. Fix Windows runtime/DLL search setup.
4. Fix package contents and public Python API mismatch.
5. Refactor plugin initialization safely.
6. Harden Python plugin loading and reentrancy handling.
7. Harden shutdown and native cleanup.
8. Improve operation metadata and operation listing.
9. Add Windows package CI/smoke tests.
10. Update docs once behavior is verified.

## Phase 0 — Baseline Reproduction

### Why

Without a minimal, repeatable reproduction, any fix may only address the local developer machine. Windows failures are especially sensitive to environment leakage from `PATH`, installed USD tools, Visual Studio, Omniverse, Houdini, or other DCC packages.

### How

Create a clean test matrix for the prebuilt Windows package.

Test dimensions:

| Dimension | Cases |
| --- | --- |
| Python ABI | Matching package ABI only, for example Python 3.12 for `py_3.12` package |
| Environment | Clean shell, no Houdini/Omniverse/USD paths, only package paths added |
| Asset type | In-memory USD, simple file-backed USD, real Kitbash USD with dependencies copied |
| API path | `import usd_optimize.core`, registry listing, single operation execution, standalone JSON execution |
| Shutdown | Normal interpreter exit, explicit core shutdown if implemented, subprocess exit code |

Create a small repro directory outside the source tree or under `tools/windows_prebuilt_repro/` with scripts that can be run against an extracted package path.

Suggested scripts:

```text
tools/windows_prebuilt_repro/
├── README.md
├── smoke_import.py
├── smoke_registry.py
├── smoke_execute_operation.py
├── smoke_standalone.py
├── smoke_materialx_dependencies.py
└── run_all.ps1
```

Each script should print:

- Python executable and version.
- Package root.
- Effective `PYTHONPATH` additions.
- Effective DLL directories / relevant `PATH` entries.
- Exact import or operation being tested.
- Exit code.

For native crashes, run the script in a subprocess from `run_all.ps1` so one access violation does not hide the rest of the matrix.

### Acceptance Criteria

- A developer can reproduce the current Windows failures from a clean shell.
- The repro scripts distinguish import failure, plugin registry failure, operation execution failure, MaterialX load failure, and shutdown crash.
- The repro scripts do not depend on local Houdini, Omniverse, or user-specific environment variables.

## Phase 1 — Add a Diagnostic / Doctor Command

### Why

Before fixing everything, users and developers need a command that says what is wrong. Current behavior can fail with native access violations or noisy USD plugin errors that do not identify the missing DLL or failing operation plugin.

### How

Add a Python diagnostic module that can run with minimal imports first, then progressively imports heavier components.

Proposed module:

```text
source/core/python/usd_optimize/diagnostics.py
```

Proposed command module:

```text
source/core/python/usd_optimize/scripts/doctor.py
```

The doctor should check, in order:

1. Python version and ABI.
2. Package root discovery.
3. Presence of expected directories:
   - `python`
   - `usdpy`
   - `lib`
   - `extraLibs`
   - operation plugin directory, if present in the package layout.
4. Presence of expected core files:
   - Python package files.
   - `_core` / implementation `.pyd` modules.
   - `usd_optimize.core.dll` or equivalent runtime library.
5. Whether `pxr` imports.
6. Whether `usd_optimize` imports.
7. Whether `usd_optimize.core` imports.
8. Whether the core registry initializes.
9. Operation count and operation keys.
10. Failed native plugins, if the C++ layer exposes this information.
11. MaterialX-related USD plugin availability.
12. Whether the documented `standalone` API is importable.

Output should support both human-readable text and JSON:

```powershell
python -m usd_optimize.scripts.doctor --package-root C:\path\to\package
python -m usd_optimize.scripts.doctor --json
```

Add a lightweight result model:

```python
@dataclass
class DiagnosticCheck:
    name: str
    status: Literal["ok", "warning", "error", "skipped"]
    message: str
    details: dict[str, Any]
```

Do not import `usd_optimize.core` at module import time in the doctor. The doctor must be able to report that `usd_optimize.core` crashes or fails in a subprocess.

### Acceptance Criteria

- `doctor` reports missing paths and missing DLL candidates before attempting plugin registry initialization.
- `doctor --json` is machine-readable enough for CI.
- A core import crash is reported as a failed check with subprocess exit code, not as a half-written terminal log.

## Phase 2 — Windows Runtime Bootstrap

### Why

Windows DLL search behavior is not equivalent to Linux `rpath`/`LD_LIBRARY_PATH`. Since Python 3.8, extension module dependency resolution often requires explicit DLL directory registration through `os.add_dll_directory()`. Relying only on `PATH` is fragile, especially for transitive dependencies loaded by `.pyd` files or plugin DLLs.

### How

Add an official runtime bootstrap function for Windows.

Proposed module:

```text
source/core/python/usd_optimize/bootstrap.py
```

Proposed API:

```python
def configure_runtime(package_root: str | os.PathLike[str] | None = None) -> RuntimeConfig:
    """Configure Python and Windows DLL search paths for a prebuilt package."""
```

Responsibilities:

- Resolve package root explicitly from an argument or infer it from `__file__` in a prebuilt layout.
- Add package Python paths when safe:
  - `python`
  - `usdpy`
- On Windows, call `os.add_dll_directory()` for:
  - `lib`
  - `extraLibs`
  - operation plugin directory if the published package contains one, for example `lib/operations`.
- Keep returned directory handles alive for the process lifetime.
- Be idempotent.
- Avoid mutating global state more than needed.
- Provide clear errors if a path is missing.

Example usage:

```python
from usd_optimize.bootstrap import configure_runtime

configure_runtime(r"C:\path\to\usd_optimize_usd_25.11_py_3.12@...windows-x86_64.release")

from usd_optimize.core import UsdOptimizeCore
```

For source-tree development, the function should either no-op cleanly or support a `source_root` mode only if it is genuinely useful.

Update docs only after testing this API against a real extracted prebuilt package.

### Acceptance Criteria

- A clean Python process can call `configure_runtime(package_root)` and then import `pxr` and `usd_optimize.core` without relying on pre-existing Houdini/Omniverse paths.
- Calling `configure_runtime()` twice does not duplicate paths or lose DLL directory handles.
- Missing directories produce actionable messages.

## Phase 3 — Public API and Packaging Consistency

### Why

A public smoke test is only valuable if it imports modules that actually ship in the package. If docs reference `usd_optimize.core.scripts.standalone`, then the package must include that module. If the project intends a different API, the docs and tests must be changed to match reality.

### How

Investigate where the supported standalone execution code currently lives.

Current source hints:

```text
source/tests/test.python/scripts/standalone.py
```

But the documented package path is:

```python
from usd_optimize.core.scripts import standalone
```

Choose one of two fixes:

### Preferred fix: promote standalone into public source package

Move or copy the supported standalone implementation into:

```text
source/core/python/usd_optimize/core/scripts/standalone.py
source/core/python/usd_optimize/core/scripts/__init__.py
```

Add tests that import it from the public path.

### Alternative fix: update docs to supported API

If the standalone script is test-only and not intended as public API, remove it from docs and replace examples with `UsdOptimizeCore.executeOperation()` / `executeConfig()` usage.

The preferred fix is better because the docs and `.agents` workflow already expect a standalone JSON execution API, and that API is useful for wrapper tools.

### Acceptance Criteria

- `from usd_optimize.core.scripts import standalone` succeeds in source-tree tests and in the prebuilt package.
- The Windows smoke check uses the same public API that users are expected to use.
- Package file inclusion rules include the new module.

## Phase 4 — Safe Plugin Initialization Refactor

### Why

`source/core/python/usd_optimize/core/__init__.py` currently calls:

```python
UsdOptimizeCore.getInstance()
```

at import time. This was added to force plugin loading onto the importing thread and avoid import-lock deadlocks when validators dispatch work through a thread pool. That motivation is valid.

However, import-time plugin initialization is still risky because importing a package now triggers native DLL loading, plugin discovery, Python plugin import, registry mutation, and `Py_AtExit` registration. On Windows, any failure in that chain can become an access violation during a normal import.

The fix must preserve the thread-safety benefit while removing or reducing the import side effect.

### How

Implement an explicit initialization API and a safe lazy-loading policy.

Possible API:

```python
from usd_optimize.core import initialize_plugins

initialize_plugins()
```

or:

```python
core = UsdOptimizeCore.getInstance(load_plugins=True)
```

Recommended design:

1. `import usd_optimize.core` should expose symbols without unconditionally loading plugins.
2. `UsdOptimizeCore.getInstance()` should return the singleton but not necessarily force all plugins unless the current API contract requires it.
3. Add explicit `initialize_plugins()` that:
   - Acquires a process-wide initialization lock.
   - Calls the C++ plugin load path once.
   - Records success/failure state.
   - Is safe to call multiple times.
4. Any method that requires plugins, such as `getOperations()` or `executeOperation()`, should either:
   - Call `initialize_plugins()` internally, or
   - Fail with a clear message if plugins have not been initialized.

Because validators previously hit a thread/import-lock deadlock, add a targeted regression test:

- Import `usd_optimize.core` on the main thread.
- Dispatch multiple calls that require plugin initialization from a `ThreadPoolExecutor`.
- Confirm no deadlock and no recursive initialization.

Do not remove the current eager import behavior until this test exists.

### Acceptance Criteria

- `import usd_optimize.core` does not crash if plugin loading would fail; plugin loading happens at an explicit or clearly documented boundary.
- The async validator/thread-pool deadlock does not regress.
- Plugin initialization is idempotent and protected against concurrent entry.
- Failures include the plugin path or initialization phase where possible.

## Phase 5 — Python Plugin Reentrancy Guard

### Why

Python operation plugins can import `usd_optimize.core` while the core is in the middle of loading plugins. That creates a recursive-initialization trap:

1. Core starts plugin loading.
2. Loader imports a Python operation plugin.
3. Python operation plugin imports `usd_optimize.core`.
4. `usd_optimize.core` may try to initialize the core again.

Even if this does not crash on Linux, it is a fragile architecture and likely worse on Windows.

### How

Harden both sides:

### Python side

- Make Python operation plugins import the smallest possible API surface.
- Prefer importing base classes from `usd_optimize.core.operation` or a lightweight module that does not initialize the registry.
- Avoid imports from the top-level `usd_optimize.core` inside operation plugin modules unless necessary.

### C++ side

Add explicit reentrancy protection around plugin loading:

```cpp
if (m_isLoadingPlugins)
{
    // Either return cleanly or produce a diagnostic, depending on current contract.
}
```

Better behavior:

- If reentered from the same thread, return the current in-progress state or no-op.
- If entered from another thread, wait on the initialization lock.
- If a previous initialization failed, expose the failure state and allow an explicit retry only if safe.

### Tests

Create a Python plugin test that intentionally imports `usd_optimize.core` during plugin registration and verifies there is no recursive crash.

### Acceptance Criteria

- Python plugin imports do not recursively trigger registry initialization.
- Reentrant plugin loading is either blocked safely or serialized safely.
- Failed Python plugin imports are reported as plugin failures, not native crashes.

## Phase 6 — Shutdown and `Py_AtExit` Hardening

### Why

If an operation succeeds and the USD exports correctly, but the Python process crashes during exit, the likely problem is cleanup order. The binding currently registers a callback through `Py_AtExit()` to drain shutdown callbacks. On Windows, DLL unload order and Python finalization order are unforgiving.

### How

Audit and harden:

```text
source/core/bindings/BindingsPython.cpp
UsdOptimizeCore::runShutdownCallbacks()
UsdOptimizeCore::shutdown or equivalent cleanup paths
plugin unload behavior
Python operation wrapper lifetime
static singleton destruction
```

Implementation points:

- Make shutdown callback execution idempotent.
- Make all shutdown paths `noexcept` at the C++ boundary.
- Never call into Python APIs after Python finalization has started.
- Avoid unloading plugin DLLs while registered operation objects or Python wrappers still depend on them.
- Add logging around shutdown callback execution in debug/verbose mode.
- Consider exposing an explicit Python method:

```python
core.shutdown()
```

or:

```python
from usd_optimize.core import shutdown
shutdown()
```

If explicit shutdown is added, document it as optional but recommended for long-running host applications.

Subprocess tests are important here because pytest running in-process may not expose interpreter-exit crashes reliably.

### Acceptance Criteria

- A subprocess can import, initialize, execute an operation, save/export USD, and exit normally with code 0.
- Calling shutdown explicitly and then exiting does not crash.
- Calling shutdown twice is safe.
- Shutdown callback exceptions do not propagate through `Py_AtExit`.

## Phase 7 — MaterialX Dependency Fix

### Why

Kitbash-style USD assets frequently reference `.mtlx` files. If the package ships `usd_usdMtlx.dll` but does not ship or locate its MaterialX dependencies, opening normal USD assets produces noisy errors such as missing MaterialX DLLs or unsupported `.mtlx` file format handling.

This is a Windows packaging issue, not an asset issue.

### How

First, confirm exactly which DLLs `usd_usdMtlx.dll` imports on the tested package.

Use one or more tools:

```powershell
dumpbin /DEPENDENTS extraLibs\usd_usdMtlx.dll
```

or a dependency scanner available in the developer environment.

Expected dependency family may include:

```text
MaterialXCore.dll
MaterialXFormat.dll
MaterialXGenShader.dll
MaterialXGenMsl.dll
MaterialXRender.dll
```

Then choose the package policy:

### Preferred fix: bundle required MaterialX runtime DLLs

- Add the required MaterialX DLLs to `extraLibs`.
- Confirm licenses/notices are correct in `THIRD_PARTY_NOTICES.md`.
- Add package validation that fails if `usd_usdMtlx.dll` has unresolved dependencies.

### Alternative fix: make MaterialX plugin optional and quiet

- If MaterialX support is not meant to be shipped, do not register `usdMtlx` by default.
- Suppress or clearly explain `.mtlx` support being unavailable.
- This is worse for production assets that reference MaterialX.

### Acceptance Criteria

- Opening a USD with `.mtlx` references does not produce missing MaterialX DLL errors in a clean package environment.
- `doctor` reports MaterialX support as available or explicitly unavailable.
- CI verifies `usd_usdMtlx.dll` dependencies resolve in the prebuilt package.

## Phase 8 — Plugin Loading Diagnostics

### Why

A plugin loader that dies with an access violation gives users no way to know which plugin failed. It also makes CI failures slow to debug.

### How

Instrument plugin loading around each stage:

1. Candidate discovery.
2. DLL load.
3. Symbol lookup.
4. Plugin init function call.
5. Operation registration.
6. Python plugin import.
7. Mapping/config loading.

Expose diagnostics in C++ and Python.

Suggested C++ record:

```cpp
struct PluginLoadDiagnostic
{
    std::string path;
    std::string name;
    std::string phase;
    bool success;
    std::string message;
};
```

Suggested Python API:

```python
core.getPluginLoadDiagnostics()
```

The loader should at minimum print the plugin path before calling the plugin initializer in verbose/debug mode.

### Acceptance Criteria

- A failing plugin can be identified by path and phase.
- `doctor` can show plugin diagnostics without requiring users to attach a debugger.
- Plugin failures do not prevent reporting previously collected diagnostics.

## Phase 9 — Operation Registry and Metadata Improvements

### Why

Tool authors should not infer operation names from DLL filenames. The observed mismatch between a DLL stem and operation key shows that filename-based wrappers are unreliable.

Also, not every operation is safe or meaningful with default arguments. Some require parameters, some are analysis-only, and some are destructive.

### How

Expose richer operation metadata from the registry.

Suggested API:

```python
core.getOperationMetadata()
```

Possible metadata fields:

```json
{
  "key": "deletePrims",
  "displayName": "Delete Prims",
  "displayGroup": "Stage",
  "description": "...",
  "author": "...",
  "version": [1, 0, 0],
  "visible": true,
  "supportsAnalysis": false,
  "runnableWithDefaults": false,
  "requiresArguments": true,
  "analysisOnly": false,
  "destructive": true,
  "experimental": false,
  "pluginPath": "..."
}
```

For the first implementation, derive what already exists:

- key
- display name
- display group
- description
- author
- version
- visible
- supports analysis
- argument schema

Then add explicit flags where source operations require them.

Prioritize known problematic operations:

- `boxClip`
- `removeAttributes`
- `sparseMeshes`

### Acceptance Criteria

- A wrapper can list valid operation keys without scanning DLL filenames.
- A wrapper can distinguish runnable default operations from parameter-required or analysis-only operations.
- Existing operation metadata tests cover at least one operation from each category.

## Phase 10 — Windows Prebuilt CI

### Why

The current issues likely slipped through because the source tree and developer environment are richer than a clean prebuilt package. CI must test the published artifact as a user receives it.

### How

Add a Windows CI job that:

1. Builds or downloads the prebuilt package artifact.
2. Extracts it into a clean temp directory.
3. Starts a clean shell with only documented environment variables.
4. Uses the matching Python ABI.
5. Runs the smoke scripts and doctor command.

Minimum smoke tests:

```python
from pxr import Usd
from usd_optimize.core import ExecutionContext, UsdOptimizeCore
```

Then:

- Create an in-memory stage.
- Attach it to an `ExecutionContext`.
- Initialize/list operations.
- Execute one simple operation.
- Import `usd_optimize.core.scripts.standalone` if it is public.
- Open a small USD with `.mtlx` reference if MaterialX is supported.
- Exit subprocess cleanly.

CI must fail on:

- Missing public modules used by docs.
- Empty operation registry.
- Native process crash.
- Missing required DLL dependency.
- MaterialX support advertised but not loadable.

### Acceptance Criteria

- Windows CI catches the current class of package failures.
- The job does not depend on Houdini, Omniverse, or installed USD.
- The CI log includes doctor output and plugin diagnostics.

## Phase 11 — Documentation Updates

### Why

Docs should describe the verified behavior, not the intended behavior. Windows users need exact instructions because small environment mistakes cause hard import failures.

### How

Update:

```text
docs/install-prebuilt-windows.md
README.md, if it has install snippets
any .agents operation invocation docs that mention standalone API
```

Doc updates should include:

- `configure_runtime()` usage if added.
- Exact DLL path requirements.
- Python ABI requirement.
- `doctor` command.
- Correct smoke test.
- How to list operations safely.
- MaterialX support expectations.
- Troubleshooting section for plugin registry failures and shutdown crashes.

### Acceptance Criteria

- A user following the Windows install doc can run the smoke test on a clean machine.
- The documented API exists in the shipped package.
- Troubleshooting entries map to diagnostics produced by `doctor`.

## Suggested Work Breakdown

### PR 1 — Reproduction and Diagnostics

- Add Windows prebuilt repro scripts.
- Add initial `doctor` command.
- Add docs for running diagnostics.

Reason: Gives visibility before invasive runtime changes.

### PR 2 — Runtime Bootstrap and Docs

- Add `usd_optimize.bootstrap.configure_runtime()`.
- Update Windows install docs.
- Add tests for idempotency and path validation.

Reason: Fixes the most obvious Windows-specific runtime setup gap.

### PR 3 — Public Standalone API Packaging

- Promote or replace `standalone.py`.
- Add source-tree and package-level import tests.
- Update smoke checks.

Reason: Fixes docs/package mismatch before users depend on it.

### PR 4 — Plugin Initialization Refactor

- Add explicit initialization API.
- Remove or gate eager import-time initialization only after tests exist.
- Add thread-pool/import-lock regression test.

Reason: High-risk architectural change; isolate it from packaging fixes.

### PR 5 — Reentrancy and Plugin Diagnostics

- Add C++ plugin load diagnostics.
- Add reentrancy guard.
- Expose diagnostics to Python.
- Add Python plugin reentrancy tests.

Reason: Makes plugin failures debuggable and prevents recursive init traps.

### PR 6 — Shutdown Hardening

- Audit and harden `Py_AtExit` callback behavior.
- Add explicit shutdown if appropriate.
- Add subprocess exit tests.

Reason: Fixes successful-operation-then-crash failure mode.

### PR 7 — MaterialX Package Fix

- Bundle or explicitly disable MaterialX runtime support.
- Add dependency validation.
- Add `.mtlx` smoke test.

Reason: Required for real production USD assets with MaterialX references.

### PR 8 — Operation Metadata

- Add richer operation metadata API.
- Mark required-parameter and analysis-only operations.
- Update wrappers/docs to use registry metadata.

Reason: Prevents wrapper tools from guessing operation names or running invalid defaults.

### PR 9 — Windows Prebuilt CI

- Add artifact-level Windows package validation.
- Run doctor and smoke tests from extracted package.

Reason: Prevents regression in future releases.

## Risk Notes

### Import-time initialization change is high risk

The current eager `getInstance()` exists to avoid a real async validator deadlock. Removing it blindly would be a regression. The correct fix is explicit initialization plus tested thread-safe lazy loading.

### Shutdown fixes are high risk

Crashes during interpreter shutdown can be sensitive to object lifetime, DLL unload order, static destruction, and Python finalization state. Subprocess tests are mandatory.

### MaterialX fixes may affect package size and licensing

Bundling MaterialX DLLs may require package-size review and third-party notice updates. Disabling MaterialX is simpler but less useful for production USD assets.

### Operation metadata can become stale

If metadata is manually duplicated outside operation definitions, it will drift. Prefer deriving metadata from `Operation` objects and only adding explicit flags where the C++ operation itself declares them.

## Definition of Done

This work is done when:

- The Windows prebuilt package can be extracted into a clean environment and pass the documented smoke check.
- `doctor` reports actionable diagnostics instead of leaving users with native crashes.
- `import usd_optimize.core` is safe and predictable.
- Plugin initialization is explicit or safely lazy, idempotent, and thread-safe.
- Python plugin reentrancy does not crash or deadlock.
- Shutdown after successful operation execution exits cleanly.
- MaterialX support is either fully functional or clearly reported as unavailable.
- Public docs reference only APIs that ship in the package.
- CI validates the extracted Windows package, not only the source tree.

## First Concrete Development Step

Start with Phase 0 and Phase 1 together:

1. Add `tools/windows_prebuilt_repro/` with subprocess-based smoke scripts.
2. Add a minimal `usd_optimize.scripts.doctor` that checks paths, imports, registry initialization, and standalone API availability.
3. Run both against the currently failing Windows package.
4. Save the output as the baseline failure report.

This gives the rest of the work a measurable target: each later PR should turn one baseline failure into either `ok` or a clear, documented `warning`.
