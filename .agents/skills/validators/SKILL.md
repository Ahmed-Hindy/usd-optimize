---
name: validators
description: Reference for Usd Optimize's validator infrastructure (registration, CLI, logging, REQUIRES_MESH cache). Do not use for ad-hoc validation runs — use run-validators instead.
version: "1.0.0"
allowed-tools: Shell
metadata:
  author: NVIDIA Corporation
  tags: [validation, performance, reference]
---

<!-- SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved. -->
<!-- SPDX-License-Identifier: Apache-2.0 -->

# Performance Validators

Usd Optimize ships a set of `usd-validation-nvidia` rules under the
**Performance** category that wrap analysis-mode operations. All rules
register together via `register_all()`.

## What this skill covers

This skill is the *reference doc* for validator infrastructure. For the day-to-day "validate this asset" workflow, use `run-validators`; for reading the report, use `interpret-validators`. Search this doc for keywords like `REQUIRES_MESH`, `cache`, `entry-point`, `register_all`, `analysisMode`, `libusd`, `auditwheel` to jump.

- **Rule families** — current shape of the rule list.
- **Programmatic invocation** — `register_all()` + `ValidationEngine().validate(stage)`.
- **Optional helper wrapper path** — `tools/perf_validators/run.{sh,bat}` when the selected Usd Optimize environment or build checkout provides it.
- **CLI invocation** — `nvidia_usd_validate` setup, with caveats around `auditwheel`, `LD_LIBRARY_PATH`, the `libusd` alignment requirement.
- **Logging to file** — CSV / JSON / log sinks.
- **Performance behavior** — analysis-result cache and the `REQUIRES_MESH` short-circuit (mesh-less stages skip mesh-only rules silently — search for `REQUIRES_MESH` to find this).
- **Gotcha — plugin discovery** — what makes the entry-point plugin importable for CLI/metadata discovery.
- **Spec compliance** — entry-point declaration matches the AVEP spec.
- **Running validator tests** — `./repo.sh test -s python`.
- **Adding a new performance validator** — recipe for new rule classes.

The authoritative list lives in `validators/__init__.py` — see the
`_RULE_CATEGORIES` tuple. Avoid duplicating it in this doc; the source is the
single source of truth.

## Rule families (current shape)

| Group | Backing op(s) |
|---|---|
| Mesh-cleanup family | `meshCleanup` |
| Duplicates / structure | `deduplicateGeometry`, `deduplicateHierarchies`, `optimizeMaterials`, `findCoincidingGeometry`, `pruneLeaves`, `findFlatHierarchies`, `flattenHierarchy`, `removePrims` |
| Renderer / performance | `rtxMeshCount`, `countVertices`, `fitPrimitives`, `sparseMeshes`, `optimizeTimeSamples`, `removeSmallGeometry`, `computeExtents` |
| Geometry checks | `findOverlappingMeshes`, `findOccludedMeshes` |
| Misc | `generateNormals`, `removeUnusedUVs`, `optimizePrimvars` |

The authoritative registered-rule list is `_RULE_CATEGORIES` in `validators/__init__.py`; check there rather than this table.

All rule classes have the `UsdOptimize` prefix (e.g. `UsdOptimizeNonManifoldChecker`).

Source: `source/core/python/usd_optimize/validators/<name>.py`. Tests: `source/tests/test.python/test_validators_*.py`.

## Programmatic invocation

```python
from usd_optimize.validators import register_all
from usd_validation_nvidia import ValidationEngine
from pxr import Usd

register_all()                         # default rules only

results = ValidationEngine().validate(Usd.Stage.Open("asset.usd"))
for issue in results.issues():
    print(issue.severity, issue.rule.__name__, issue.message)
```

`register_all()` is idempotent.

## Optional helper wrapper path

For ad-hoc validation and comparing runs (e.g. before/after an operation
parameter change) from a source checkout, use `tools/perf_validators/run.sh`
(Linux) or `tools/perf_validators/run.bat` (Windows) only when those wrappers
are present. They set up the build-tree library paths and invoke
`perf_validators.py` under the bundled Python. **Prefer this over the
`nvidia_usd_validate` CLI** for dev-tree runs (see caveats below).

> **Dev-tree only.** Both wrappers point at `_build/$platform/$config/...`
> from the local checkout. They assume `./repo.sh build` has already run.
> Do not assume Kit or standalone Usd Optimize installs provide them, and do not use
> them for a pip-installed deployment — for that path, see *CLI invocation*
> below.

```bash
# Run against an asset, write a small summary JSON
tools/perf_validators/run.sh run path/to/asset.usd --summary before.json

# ...edit the asset or change validator/op defaults, rebuild...

tools/perf_validators/run.sh run path/to/asset.usd --summary after.json

# Diff: per-rule counts + total + validate-time delta
tools/perf_validators/run.sh compare before.json after.json
```

`run` also accepts `--csv` (per-issue CSV, validator format), `--json` (full
validator JSON), `--fix <path>` (run `IssueFixer` on Usd Optimize issues
and write the fixed stage there). The `--summary` JSON is the format `compare`
reads — it is purpose-built for diffing and is independent of the validator's
JSON shape.

The wrapper requires `./repo.sh build` to have run; it auto-installs
`usd-validation-nvidia` into the bundled Python on first use.

## CLI invocation

The `nvidia_usd_validate` CLI ships with `usd-validation-nvidia`. Using it
to drive Usd Optimize's rules requires the `usd-optimize`
wheel.

**Checkout default:** Prefer **`tools/perf_validators/run.{sh,bat}`** (same as *Optional helper wrapper path* above)—it aligns `PYTHONPATH` / loaders with `./repo.sh build`.

**Alternative — CLI + `pip install`:** Needed when callers require the upstream `nvidia_usd_validate` entry binary and discovery via wheel metadata. Several gotchas below.

### Building and installing the wheel

`usd-optimize` is **not on PyPI**. `./repo.sh build` produces shared
libraries; the wheel is a separate target:

```bash
./repo.sh build         # required first
./repo.sh py_package    # produces _build/packages/usd_optimize-*.whl
# Wheel metadata declares Python 3.12-only unless you rebuilt first with `./repo.sh --set-token python_ver:3.10 py_package`
# or `python_ver:3.11`.
python3.12 -m pip install _build/packages/usd_optimize-*.whl
```

Caveats:

- **Host toolchain (Linux).** `auditwheel repair` needs **`patchelf`** installed (`sudo apt-get install patchelf`). Without it, repair fails before wheels land under `_build/packages/`.
- **Network.** `tools/pyproject/pybuild.sh` bootstraps a venv under `_build/host-deps/py_package_venv/` and pip-installs Poetry, auditwheel, and tooling from PyPI. Air‑gapped or blocked hosts must pre-seed equivalents.
- **`py_package` venv wedged:** If bootstrap failed part‑way but `_build/host-deps/py_package_venv/` exists, the helper may reuse a broken env and invoke an incompatible system Poetry. **`rm -rf _build/host-deps/py_package_venv`** and rerun `./repo.sh py_package`.

- **Toolchain assumption (Linux).** The `auditwheel` repair step that runs
  inside `py_package` targets manylinux_2_35. On distros newer than the build
  matrix (e.g. GCC 13 / Ubuntu 24.04, which produces manylinux_2_39 binaries),
  the repair fails and `py_package` exits non-zero. The unrepaired wheel
  staged at `_build/pyproject/dist/*.whl` is still installable locally — but
  it ships only the operation plugin libs, **not** the Usd Optimize core
  libs (those are normally bundled by auditwheel). To use it you must point
  the loader at your build tree (next bullets).
- **`LD_LIBRARY_PATH` (Linux).** **`auditwheel` repair** bundles many Usd Optimize deps into **`usd_optimize.libs/`** (`RPATH` usually resolves them — **often no `LD_LIBRARY_PATH` needed** except when troubleshooting). **`auditwheel` repair fails:** install the unstaged/unrepaired wheel from `_build/pyproject/dist/` and export dev-tree loaders:

  ```bash
  export LD_LIBRARY_PATH=_build/$platform/release/lib:_build/$platform/release/extraLibs:$LD_LIBRARY_PATH
  ```

- **`PYTHONPATH` / dual `libusd` (Linux, repaired wheel vs `usd-exchange`):** Even after repair, **`pxr` is supplied by `usd-exchange`**, which may vendor a **different** auditwheel‑mangled `libusd_*.so` than the copy inside `usd_optimize.libs/`. If so, **`UsdUtilsStageCache` splits** and validators error with missing stage IDs. **Treat `PYTHONPATH` alignment as mandatory** unless you verified (e.g. `ldd` on `Usd/_usd.so` vs Usd Optimize's `UsdUtils` linkage) both stacks resolve the **same** `libusd`:

  ```bash
  export PYTHONPATH=_build/$platform/release/python:_build/target-deps/usd/release/lib/python:$PYTHONPATH
  ```

The optional helper wrapper `tools/perf_validators/run.sh` sets **`PYTHONPATH` + `LD_LIBRARY_PATH`** for checkout builds; the raw **`nvidia_usd_validate` CLI does not**.

Track packaging work to unify `usd-exchange`'s USD with the repaired wheel artifact so this alignment step disappears for typical `pip` consumers.

### Prebuilt deployment

If you've received a **fully-repaired** wheel (manylinux\_2\_35 toolchain), a plain **`pip install`** often suffices—but **still verify** dual-`libusd` does not recur (wheel + `usd-exchange` layout can change).

```bash
python3.12 -m pip install usd_optimize-*.whl   # interpreter must satisfy wheel tags
nvidia_usd_validate path/to/asset.usd
```

What you typically **don't** need for **repaired wheels:** manual `LD_LIBRARY_PATH` pointing at `./repo.sh` `_build/` (bundled libs cover it).

What consumers **might** still need: **`PYTHONPATH` alignment** toward the Usd Optimize build's USD whenever `usd-exchange` introduces a mismatched `pxr` linkage (see bullets above)—same remediation as checkout CLI installs.

Once the `usd-optimize` wheel is installed, its rules load automatically — the new `PluginManager` auto-discovers and loads every plugin it finds, with no allow-list env var needed (see *Gotcha — plugin discovery* below).

To verify discovery: **`nvidia_usd_validate --help | grep UsdOptimize`** (the `-r/--rule` argument's choices enumerate every discovered rule class, so registered `UsdOptimize*` rules appear there). Key success off **`grep`'s exit code**.

### Running the CLI

```bash
# Once the usd-optimize wheel is installed, its rules load automatically —
# no env var needed (see "Gotcha — plugin discovery" below).

nvidia_usd_validate path/to/asset.usd                              # default + Performance rules
nvidia_usd_validate -c Performance asset.usd                       # only the Performance category
nvidia_usd_validate -r UsdOptimizeRtxMeshCountChecker asset.usd # one rule
```

Note: the entry-point plugin only registers the default rule set. To run
`FindOverlappingMeshes` from the CLI, register it manually before invoking the
validator.

### Known CLI issues

- **`pxr` and the C++ core must resolve to the same `libusd`.** Tracked as
  a packaging follow-up (coordinate `usd-exchange` + repaired wheel linkage).
  **Linux — default workaround:** prepend the Usd Optimize build's USD bindings before invoking **`nvidia_usd_validate`**:

  ```bash
  export PYTHONPATH=_build/$platform/release/python:_build/target-deps/usd/release/lib/python:$PYTHONPATH
  export LD_LIBRARY_PATH=_build/$platform/release/lib:_build/$platform/release/extraLibs:$LD_LIBRARY_PATH
  ```

  The helper wrapper **`tools/perf_validators/run.sh`** does this automatically; **`nvidia_usd_validate` does not.**

  Skip it only after demonstrating one `UsdUtilsStageCache` (e.g. both `Usd/_usd.so` and `libusd` used by Usd Optimize resolve identical `libusd_*.so`).

  Failures cite the offending stage ID and mismatch hypothesis (see `Operation.cpp`).

  *Why it happens:* multiple `libusd` images can load (`usd_optimize.libs/`, **`usd-exchange`’s libs**, unstaged `_build/` SOs …). **`UsdUtilsStageCache::Get()` is a static per image**, so stages registered from Python-visible `pxr` are invisible across a mismatched Usd Optimize core.

- **`--help` does not group rules by category.** Upstream
  `nvidia_usd_validate` lists every discovered rule under the
  `-r/--rule` choices (so `UsdOptimize*` rules are visible there) but
  doesn't surface the plugin-registered category taxonomy. Use this
  skill doc as the index for the Performance grouping until the upstream
  CLI gains category-aware help.

## Logging to file

Three sinks; mix and match:

```bash
# CSV: one row per issue (Asset, Rule, Message, Severity, Suggestion, Location).
nvidia_usd_validate asset.usd --csv-output issues.csv

# JSON: structured per-rule with full prim/property paths under "at".
nvidia_usd_validate asset.usd --json-output issues.json

# Capture C++ stdout/stderr and Python logging together:
nvidia_usd_validate asset.usd --json-output issues.json > validation.log 2>&1
```

Programmatic equivalents:

```python
from usd_validation_nvidia import IssueCSVData, export_json_file
import logging

logging.basicConfig(filename="validation.log", level=logging.INFO)   # validator lifecycle messages
IssueCSVData.from_(results).export_csv("issues.csv")
export_json_file("issues.json", [results])
```

Note: the C++ `[INFO]/[DEBUG]` lines from Usd Optimize operations go to **stdout**, not Python `logging` — capture them at the shell level if needed.

## Performance behavior

The base class includes two optimizations that callers should know about.

### Analysis-result cache

Many rules wrap the same op with the same args (e.g. the mesh-cleanup-family rules read different fields of one `meshCleanup` result). The base class caches analysis output per `(root-layer-identifier, op_name, args)` so the analysis runs once per stage and the rest hit the cache.

**Lifetime**: cache persists for the life of the Python process. If a stage is mutated between `engine.validate(stage)` calls, the cached result is stale. Long-lived host processes that revalidate the same stage after edits should call:

```python
from usd_optimize.validators import clear_analysis_cache
clear_analysis_cache()
```

### Mesh-only short-circuit

Mesh-only rules early-out on stages with no `UsdGeomMesh`. The "has mesh" check is itself cached per stage. Rules that target hierarchy / materials / animation set `REQUIRES_MESH = False` so they keep running on mesh-less stages.

## Gotcha — plugin discovery

`usd-validation-nvidia>=1.19.3`'s `PluginManager` auto-discovers and loads
**all** plugins it finds — it scans both the `usd_validation_nvidia` and the
`omni.asset_validator` entry-point groups via `importlib.metadata` and loads
every entry regardless of entry-point name. There is **no allow-list env var**:
once the package providing a plugin is importable, its rules load
automatically. So:

- **Programmatic users** call `register_all()` and don't depend on metadata
  discovery at all.
- **CLI users** must **pip-install `usd-optimize`** so the `registrant`
  entry-point is in `importlib.metadata` (the wheel declares it; a source
  checkout on `PYTHONPATH` does **not** expose it). Nothing else is needed —
  the loader picks it up and the rules register.

If `nvidia_usd_validate --help` shows no `UsdOptimize*` rules: the wheel is
missing from the interpreter `nvidia_usd_validate` runs on
(`python -m pip show usd-optimize`). When only `DefaultPlugin` appears in INFO
logs, suspect that missing-metadata case (source-only `PYTHONPATH`), and either
pip-install the wheel or use `register_all()` / `tools/perf_validators/run.sh`.

## Spec compliance

Our entry-point declaration follows the *Asset Validator Entrypoint Plugins* spec:

```toml
[project.entry-points."omni.asset_validator"]
registrant = "usd_optimize.validators:UsdOptimizeValidatorPlugin"
```

Discovery query: `importlib.metadata.entry_points(group="omni.asset_validator", name="registrant")`. The `usd-validation-nvidia` loader scans both this `omni.asset_validator` group and the newer `usd_validation_nvidia` group, so the existing declaration is still discovered as-is. The class exposes `on_startup()` / `on_shutdown()` (instance methods, accepted per the spec).

## Running validator tests

```bash
# Run validator tests as part of the standard python suite:
./repo.sh test -s python
```

The repo's Python test wrapper currently runs the full `python` suite; it does
not forward `-e` / `-k` filters to `source/tests/test.python/run_discover.py`.

## Adding a new performance validator

1. Add a new rule class under `source/core/python/usd_optimize/validators/<name>.py`, subclassing `UsdOptimizeRuleBase` from `_base.py`. Set `OPERATION_NAME` and `DEFAULT_ARGS`; override `_translate(stage, analysis)` to convert the operation's analysis JSON into `_AddWarning` / `_AddFailedCheck` / `_AddError` calls.
2. Set `REQUIRES_MESH = False` if the rule targets hierarchy / materials / animation rather than `UsdGeomMesh` content (see `flat_hierarchies.py` for an example). Defaults to `True`.
3. Re-export it from `validators/__init__.py` and add it (with its category) to the `_RULE_CATEGORIES` tuple in that same file. All rules register together — there is no default/opt-in split.
4. Add a test file `source/tests/test.python/test_validators_<name>.py` that opens a fixture stage, enables the rule on a `ValidationEngine(init_rules=False)`, and asserts on issue count + severity.
5. Update the smoke test (`test_validators_smoke.py`) `EXPECTED_RULES` tuple.
6. Rebuild — `source/core/premake5.lua` already copies the whole `validators/` tree into the wheel.

If the operation you want to back the rule with doesn't yet support analysis mode, add `getSupportsAnalysis()` + `executeAnalysisImpl()` to the C++ operation first (see `PLUGINS.md` § Analysis Mode).

## Purpose

Reference doc for Usd Optimize's `usd-validation-nvidia`
integration: rule families, programmatic vs. CLI invocation, plugin
discovery, libusd alignment, the analysis-result cache, the
`REQUIRES_MESH` short-circuit, and the recipe for adding a new rule
class. Other skills (`run-validators`, `interpret-validators`,
`new-operation`) link here for infrastructure details rather than
duplicating them.

## Prerequisites

- A local Usd Optimize checkout when using checkout-provided helper
  wrappers or running tests; do not assume Kit or standalone Usd Optimize installs
  provide those wrappers.
- A Python interpreter that can import `usd_optimize` and
  `usd_validation_nvidia`. The optional helper wrappers handle this for
  dev-tree runs; CLI use needs the appropriate `PYTHONPATH` /
  `LD_LIBRARY_PATH` setup described above.
- `usd-validation-nvidia` installed in the active Python (the dev
  driver auto-installs on first use; CLI users install via pip).

## Limitations

- This is a **reference doc**, not a workflow. For day-to-day "validate
  this asset" use, invoke the `run-validators` skill. For reading the
  resulting artifacts, invoke `interpret-validators`.
- The `nvidia_usd_validate` CLI has known quirks — `--help` doesn't
  group rules by category; **`pxr`** (often from **`usd-exchange`**) **and**
  Usd Optimize's C++ stack must bind the **same** `libusd` image (**dual-`libusd`**, `UsdUtilsStageCache` mismatches otherwise). **`tools/perf_validators/run.sh`**
  sets `PYTHONPATH` / `LD_LIBRARY_PATH` against `./repo.sh build` checkout trees; **`nvidia_usd_validate` pip installs** typically need parallel exports from the same `_build/` tree (`_build/$platform/release/…`) unless packaging guarantees a unified USD stack — see *CLI invocation*. Prefer **`run-validators`/dev driver unless** callers require the upstream CLI binary.
- Adding a new rule still requires C++ changes if the backing
  operation lacks analysis mode — see `PLUGINS.md` § Analysis Mode.

## Troubleshooting

| Symptom | Likely cause | Fix |
|---|---|---|
| `nvidia_usd_validate --help` shows no `UsdOptimize*` rules | `usd-optimize` not pip-installed, so metadata has no `registrant` entry-point (common with source-only `PYTHONPATH`). | `pip install` the wheel (`./repo.sh py_package`) so the plugin auto-loads (see *Gotcha — plugin discovery*), or use `register_all()` / `tools/perf_validators/run.sh`. |
| Validator returns stage-id / cache / "`libusd`" mismatch errors | **`pxr` + C++ load different `libusd` images** (repaired wheel + separate `usd-exchange` libs vs `_build/`). | Prefer **`tools/perf_validators/run.sh`**. Otherwise set **`PYTHONPATH` _and_ `LD_LIBRARY_PATH`** from *Known CLI issues* (`_build/$platform/release/...`). |
| Stage edited but cached results stale | Analysis-result cache survives the Python process. | Call `clear_analysis_cache()` between runs. |
| Mesh-only rules silently skipped on a stage that obviously has meshes | `REQUIRES_MESH` short-circuit decided the stage has none — usually because meshes live below an unloaded payload. | Open the stage with `Usd.Stage.Open(path, Usd.Stage.LoadAll)` before validating. |
| `auditwheel` repair fails on Ubuntu 24.04 | Distro produces manylinux_2_39 binaries; `py_package` targets `_2_35`. | Install the unrepaired wheel from `_build/pyproject/dist/` and set `LD_LIBRARY_PATH` per the *CLI invocation* section. |
