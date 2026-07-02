# Installing the Prebuilt Usd Optimize Package on Windows

This guide is for **consumers of a published `usd_optimize` package** on Windows — for example, a drop named like:

```
usd_optimize_usd_<usd_ver>_py_<py_ver>@<version>.<platform>.release
```

If you are building Usd Optimize from source, see the top-level [README](../README.md) and use `repo.bat build` / `repo.bat test` instead. The published package does **not** include `repo.bat`, source code, or test fixtures — only headers, prebuilt libraries, and Python bindings.

## Package Layout

| Directory | Purpose |
| --- | --- |
| `include/` | C++ public headers (`usd_optimize/core/`) |
| `lib/` | Prebuilt DLLs and Windows import libraries (`usd_optimize.core.dll`, plugin DLLs, `operation_mapping.json` — deprecated-name aliases for `map_config()`, not the list of operations) |
| `python/` | Python bindings (`usd_optimize.core`) and bundled tests under `python/tests/test.python/` |
| `usdpy/` | OpenUSD Python runtime modules (`pxr.*`) — the package brings its own USD |
| `extraLibs/` | Third-party runtime libraries (Alembic, MaterialX, OpenSubdiv, TBB) and the matching CPython runtime DLL (e.g. `python312.dll` for `py_3.12`) |

There is **no `python.exe` in the package** — you must supply your own interpreter that matches the package's Python ABI.

## Prerequisites

### Python — must match the package name

The Python version is encoded in the package directory name (`py_3.12` in the example above). The bundled USD `.pyd` modules link against `python312.dll`, so loading them under any other Python (3.10, 3.11, 3.13, …) fails with:

```
ImportError: Module use of python312.dll conflicts with this version of Python.
```

This is a hard ABI requirement, not a preference. Install the matching Python — for the `py_3.12` package:

```powershell
winget install --id Python.Python.3.12 --scope user
```

User-scope keeps the installer out of `C:\Program Files\` and avoids touching any system Python you already have.

### C++ runtime (only if you link against the C++ libraries)

You only need the **Microsoft Visual C++ Redistributable** (or a Visual Studio install with the C++ workload) on the target machine if you are linking your own C++ application against `usd_optimize.core.lib`. Pure-Python consumers can skip this — `python312.dll` and the bundled USD/TBB DLLs cover the runtime needs.

## Installing

### 1. Extract the package

Place the unpacked directory anywhere — for the rest of this guide we assume it lives at:

```
%PACKAGE_ROOT% = C:\path\to\usd_optimize_usd_25.11_py_3.12@<version>.windows-x86_64.release
```

### 2. (Recommended) Create a Python virtual environment

A venv keeps Usd Optimize's `PYTHONPATH` tweaks isolated from any other Python project on the machine:

```powershell
$root = "C:\path\to\usd_optimize_usd_25.11_py_3.12@<version>.windows-x86_64.release"
& "$env:LOCALAPPDATA\Programs\Python\Python312\python.exe" -m venv "$root\.venv"
```

Adjust the interpreter path to wherever your matching Python lives (`py -3.12 -c "import sys; print(sys.executable)"` will print it).

### 3. Set environment variables

Two paths must be exported every session:

| Variable | Why |
| --- | --- |
| `PYTHONPATH` += `python;usdpy` | Lets the interpreter find both `usd_optimize.*` and `pxr.*` |
| `PATH` += `lib;extraLibs;lib\operations` | Lets Windows resolve transitive DLL dependencies for USD, TBB, Alembic, core bindings, and operation plugins |

PowerShell:

```powershell
$root = "C:\path\to\usd_optimize_usd_25.11_py_3.12@<version>.windows-x86_64.release"
$env:PYTHONPATH = "$root\python;$root\usdpy;$env:PYTHONPATH"
$env:PATH = "$root\lib;$root\extraLibs;$root\lib\operations;$env:PATH"
```

cmd.exe:

```bat
set PACKAGE_ROOT=C:\path\to\usd_optimize_usd_25.11_py_3.12@<version>.windows-x86_64.release
set PYTHONPATH=%PACKAGE_ROOT%\python;%PACKAGE_ROOT%\usdpy;%PYTHONPATH%
set PATH=%PACKAGE_ROOT%\lib;%PACKAGE_ROOT%\extraLibs;%PACKAGE_ROOT%\lib\operations;%PATH%
```

To make the settings durable, wrap them in an activation script (e.g. extend `.venv\Scripts\activate.ps1`) or set them via the **System Properties → Environment Variables** dialog.

### 4. Bootstrap DLL directories from Python

For Python 3.8+, setting `PATH` alone is not always enough for extension modules and plugin DLLs. Before importing `pxr` or `usd_optimize.core`, call the package bootstrap helper once:

```python
from usd_optimize.bootstrap import configure_runtime

configure_runtime(r"C:\path\to\usd_optimize_usd_25.11_py_3.12@<version>.windows-x86_64.release")
```

The helper is idempotent. It adds `python` and `usdpy` to `sys.path`, prepends the runtime DLL directories to `PATH`, and registers `lib`, `extraLibs`, and `lib\operations` with `os.add_dll_directory()` on Windows.

## Verifying the Install

A two-step smoke test confirms the bindings load and a real operation executes against an in-memory USD stage. Save the script as `smoke_check.py` in the extracted package root and run it with the matching Python.

```python
# smoke_check.py
import json
from pathlib import Path

from usd_optimize.bootstrap import configure_runtime

package_root = Path(__file__).resolve().parent
configure_runtime(package_root)

from usd_optimize.core import ExecutionContext, UsdOptimizeCore
from usd_optimize.core.scripts import standalone
from pxr import Usd, UsdGeom

# 1. Bindings + USD load
ctx = ExecutionContext()
assert ctx.usdStageId == -1
stage = Usd.Stage.CreateInMemory()
assert ctx.set_stage(stage) and ctx.usdStageId != -1
ctx.remove_stage()
print("[1/3] bindings + USD: OK")

# 2. Op registry populated
core = UsdOptimizeCore.getInstance()
ops = core.getOperations()
assert len(ops) > 0
print(f"[2/3] op registry: {len(ops)} operations registered")

# 3. End-to-end through the public 'standalone' API
stage = Usd.Stage.CreateInMemory()
UsdGeom.Xform.Define(stage, "/World")
UsdGeom.Cube.Define(stage, "/World/c1")
UsdGeom.Cube.Define(stage, "/World/c2")
ops_json = json.dumps([
    {"operation": "executionContext", "verbose": False},
    {"operation": "deletePrims", "primPaths": ["/World/c1"]},
])
assert standalone.execute_commands_from_json(stage, ops_json)
assert sum(1 for _ in stage.TraverseAll()) == 2  # one prim removed
print("[3/3] standalone.execute_commands_from_json: OK")

print("\nALL SMOKE CHECKS PASSED")
```

Run it:

```powershell
& "$root\.venv\Scripts\python.exe" smoke_check.py
```

Expected output:

```
[1/3] bindings + USD: OK
[2/3] op registry: <N> operations registered
[3/3] standalone.execute_commands_from_json: OK

ALL SMOKE CHECKS PASSED
```

The exact value of `<N>` varies by build — any positive number confirms the plugins loaded.

## Using Usd Optimize in Your Code

The public Python entry point is `usd_optimize.core.scripts.standalone`. It accepts a `Usd.Stage` and a list of operation descriptors as JSON:

```python
from usd_optimize.bootstrap import configure_runtime

configure_runtime(r"C:\path\to\usd_optimize_usd_25.11_py_3.12@<version>.windows-x86_64.release")

from usd_optimize.core.scripts import standalone
from pxr import Usd

stage = Usd.Stage.Open("scene.usd")
ops = """[
    {"operation": "executionContext", "verbose": true},
    {"operation": "merge"},
    {"operation": "optimizeMaterials"}
]"""
ok = standalone.execute_commands_from_json(stage, ops)
stage.Save()
```

Valid **`operation`** strings are whatever the loaded plugins register — enumerate them at runtime with `UsdOptimizeCore.getInstance().getOperations()` (the exact count varies by build). The bundled tests under `python/tests/test.python/` show descriptor JSON for many operations. **`lib/operation_mapping.json` is not that catalog:** it only lists deprecated operation keys and a few legacy argument renames for `standalone.map_config()`, so keys such as `merge`, `deletePrims`, or `decimateMeshes` will not appear there. The full per-operation argument reference is in the [Usd Optimize user manual](https://docs.omniverse.nvidia.com/extensions/latest/ext_scene-optimizer/user-manual.html).

## Notes on the Bundled Tests

`python/tests/test.python/` ships the full Python suite from the repository plus `run_discover.py`. **Do not expect `run_discover.py` to pass on a minimal binary-release install.**

- **`test_validators_*.py`** depend on NVIDIA **`usd-validation-nvidia`** from [PyPI](https://pypi.org/project/usd-validation-nvidia/) (`pip install usd-validation-nvidia`). They import `usd_validation_nvidia`; without that package you get **`ModuleNotFoundError: No module named 'usd_validation_nvidia'`** (one failure line per module at import time).

- **`run_discover.py` imports every `test_*.py` before unittest runs.** If **any** import fails, it prints all import failures to stderr and **`sys.exit(1)` without running tests** — so a typical release sees validator import errors only and **executes zero tests**, not a long report of fixture misses. Only after every module imports successfully does the runner execute tests; **many** of those tests expect USD fixtures under `../data`, which exists in the source tree but not in the published package.

The self-contained tests in `test_core_python_bindings.py` (`test_executionContext`, `test_executionContext_reportPath_roundtrip`, `test_executionContext_reportPath_survives_executeOperation`, `test_usdOptimizeCore`, `test_operation`) are equivalent to the smoke-check above.

## Troubleshooting

**`ImportError: Module use of python312.dll conflicts with this version of Python.`**
Your interpreter does not match the package's `py_<version>` token. Install the matching Python.

**`ImportError: DLL load failed while importing _tf` (or another `pxr` module)**
`PATH` is missing `lib`, `extraLibs`, or `lib\operations`, or `configure_runtime()` was not called before importing native modules. Set the paths and restart the interpreter before importing `pxr` or `usd_optimize.core`.

**`ModuleNotFoundError: No module named 'usd_optimize'` or `'pxr'`**
`PYTHONPATH` is missing `python` or `usdpy`. Both directories must be on `PYTHONPATH`.

**`ModuleNotFoundError: No module named 'usd_validation_nvidia'`** (common when running bundled `run_discover.py`)
The `test_validators_*.py` modules require PyPI **`usd-validation-nvidia`** (`pip install usd-validation-nvidia`). Without it, `run_discover.py` fails during its import phase and runs no tests. Prefer `test_core_python_bindings.py` or the [smoke check](#verifying-the-install) for package verification alone.

**`UsdOptimizeCore.getInstance().getOperations()` returns an empty list**
The plugin DLLs in `lib\operations` did not load. Confirm `lib`, `extraLibs`, and `lib\operations` are on `PATH`, call `configure_runtime()` before importing `usd_optimize.core`, verify no DLLs were quarantined by antivirus, and confirm the package matches your platform (`windows-x86_64`).
