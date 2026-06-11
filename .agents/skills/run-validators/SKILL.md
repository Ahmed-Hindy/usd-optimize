---
name: run-validators
description: Run Usd Optimize's performance validators against a USD asset and save artifacts for interpret-validators. Use when validating a USD.
version: "1.0.0"
allowed-tools: Bash
metadata:
  author: NVIDIA Corporation
  tags: [usd, validation, performance]
---

<!-- SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved. -->
<!-- SPDX-License-Identifier: Apache-2.0 -->

# run-validators — Execute validation and save artifacts

> **Invocation.** This is the `run-validators` skill. In Claude Code it's also
> available as the alias `/run-validators`. In Codex or other agents, invoke it
> by name.
>
> **Python invocation.** Examples below use `python3` (POSIX). On Windows use
> `py -3` (Python launcher) or the bundled interpreter at
> `_build\target-deps\python\python.exe`. Optional helper scripts referenced
> below (`resolve_artifacts.py`, `summarize_csv.py`) may be used only when the
> selected Usd Optimize environment or build checkout provides them. Do not assume Kit,
> standalone package, or wheel installs ship these repo helper wrappers.
>
> **Windows shell.** Snippets target PowerShell (Claude Code's and Codex's
> default Windows shell). The cmd.exe equivalents are obvious — `$Var` →
> `%VAR%`, backtick line continuation → `^`, `New-Item -ItemType Directory
> -Force` → `if not exist ... mkdir`. The `run.bat` wrapper itself is cmd
> internally, but it can be invoked from any shell.

Drives the usd-validation-nvidia engine over a USD file via the build's bundled
Python. The driver registers Usd Optimize's `UsdOptimize*` rules **and**
the usd-validation-nvidia base `DefaultPlugin` rules, so a single run covers both
families.

Artifacts (CSV + summary JSON + run log) are written to a stable per-asset
directory so the companion `interpret-validators` skill can replay them
without re-running.

For the reference doc on the underlying validator infrastructure (programmatic
API, CLI gotchas, entry-point allow-list, cache behavior), see the `validators`
skill.

---

## What this skill covers

Each section below is load-bearing — read past Step 4 before concluding info is missing. Search for keywords like `REQUIRES_MESH`, `base rules`, `family`, `expensive`, `mesh-less`, `long-running` to jump.

- **Usage** — flags and positional args.
- **Step 1** — input validation.
- **Step 2** — artifact-dir resolution (cross-platform helper).
- **Step 3** — driver invocation when optional helper wrappers are present,
  plus standalone analysis-mode fallback.
- **Step 4** — terse summary, plus the *Zero Scene-Optimizer issues is normal on some assets* callout (`REQUIRES_MESH` short-circuit on mesh-less stages).
- **Errors to handle** — failure modes table.

Companion skills:
- `validators` — reference doc for the underlying infrastructure (programmatic API, REQUIRES_MESH cache details, entry-point allow-list, CLI gotchas).
- `interpret-validators` — reads the artifacts and presents a structured report.
- `run-operations` — runs the recommended fix ops once you've interpreted the report.

---

## Usage

The skill takes one positional argument — the path to a USD asset — plus
optional flags:

| Argument / Flag | Meaning |
|---|---|
| `<path/to/asset.usd>` | Required. `.usd` / `.usda` / `.usdc` / `.usdz`. |
| `--foreground` / `-f` | Block on the run instead of starting it as a long-running command. Use only for tiny test fixtures. Default is long-running because validation on real assets takes minutes. |
| `--logs-dir <dir>` | Override the default artifact directory. |

**Workflow:**

1. Pass the asset path as a positional argument.
2. Run `resolve_artifacts.py` to get the artifact dir (Step 2).
3. Use `run.sh` / `run.bat` to execute the driver (Step 3).
4. Pass `--foreground` only for tiny fixtures; default to background
   execution for real assets.

If no path is provided, ask:
> "Which USD file should I validate? Please provide the full path."

### Standalone-path applicability

The wrappers `tools/perf_validators/run.sh` / `run.bat` are optional helper
wrappers, not standalone Usd Optimize or Kit requirements. On a standalone Scene
Optimizer path without these wrappers, use analysis-mode operations directly
for the Usd Optimize rule family and run the project-managed usd-validation-nvidia separately
when base rules matter.

**Runtime-aware hard-skip for Usd Optimize-specific validator names.** When the active
runtime is standalone Usd Optimize without the `usd_optimize.validators`
extension, the `UsdOptimize*` validator rules are not available unless the
user has also installed `usd-validation-nvidia` and explicitly registered
the Usd Optimize rules into it. Without that explicit setup, do not recommend or list
UsdOptimize-prefixed validator names as runnable checks; they will fail to
register or report 0 findings, which users may misread as "asset is clean."
Fall back to analysis-mode operations and explain the validator surface is
partial.

---

## Step 1 — Validate the input

A path that doesn't exist or isn't a USD file should be rejected before doing
any other work. If the selected checkout provides `resolve_artifacts.py`, use
it for this — it returns an `error` field for non-existent paths. If the
extension isn't `.usd*`, refuse with a clear message.

## Step 2 — Resolve the artifact directory

Choose or reuse a per-asset artifact directory. If the selected Usd Optimize environment
or build checkout provides the cross-platform helper, you may use it; otherwise
set the artifact paths explicitly before Step 3.

```bash
# POSIX (bash, zsh)
python3 tools/perf_validators/resolve_artifacts.py "<asset>" [--logs-dir <dir>]
```
```powershell
# Windows (PowerShell)
py -3 tools\perf_validators\resolve_artifacts.py "<asset>" [--logs-dir <dir>]
```

When used, the helper prints a single JSON object on stdout with keys:
`artifact_dir`, `csv`, `summary`, `log`, `asset_abs`, `state`, `csv_mtime`,
`asset_mtime`. Parse it (or shell out to `jq`) to get the paths used in Step 3.

The optional helper's artifact dir defaults to
`<temp>/usd-optimize-validation/<sha1(asset_abs)>/` where `<temp>` is
`$TMPDIR` / `%TEMP%` / `/tmp` depending on platform. The same hash is
recomputed by the `interpret-validators` skill when the helper is available,
so subsequent runs on the same asset overwrite the same files.

## Step 3 — Invoke the driver

When optional Usd Optimize helper wrappers are available, use the wrapper that matches
the host OS:

| Platform | Wrapper |
|----------|---------|
| Linux | `tools/perf_validators/run.sh` |
| Windows | `tools\perf_validators\run.bat` |

When present, the wrappers set up the selected Python, `LD_LIBRARY_PATH` /
`PATH`, and `PYTHONPATH`, then invoke `perf_validators.py`. They take the same
arguments. **When using this path, go through the wrapper for the driver —
never invoke `_build\target-deps\python\python.exe perf_validators.py`
directly.** The wrapper prepends the selected USD/Python paths so they win
over any ambient USD install on the user's system; calling the bundled
interpreter raw inherits the user's `PYTHONPATH` and will fail with errors
like `<dll> conflicts with this version of Python` or USD-version mismatches.
Optional pure-stdlib helpers can run without the wrapper, but the driver needs
the wrapper's environment when using this path.

**Always redirect stdout/stderr to `<artifact_dir>/run.log`** rather than
piping through `tail` — pipes buffer until the upstream process exits, so a
`tail -N` filter hides all in-progress output. A log file is tailable in real
time during long runs and is persistent for `interpret-validators` to read later.

If using `resolve_artifacts.py`, remember it is a pure resolve — it does
**not** create the artifact directory. Make it before the driver invocation
here, since this is the step that writes into it.

POSIX:

```bash
ARTIFACT_DIR="<from Step 2>"
ASSET_ABS="<from Step 2>"
mkdir -p "$ARTIFACT_DIR"

tools/perf_validators/run.sh run "$ASSET_ABS" \
    --csv "$ARTIFACT_DIR/issues.csv" \
    --summary "$ARTIFACT_DIR/summary.json" > "$ARTIFACT_DIR/run.log" 2>&1
```

Windows (PowerShell):

```powershell
$ArtifactDir = "<from Step 2>"
$AssetAbs    = "<from Step 2>"
New-Item -ItemType Directory -Force -Path $ArtifactDir | Out-Null

& tools\perf_validators\run.bat run $AssetAbs `
    --csv "$ArtifactDir\issues.csv" `
    --summary "$ArtifactDir\summary.json" *> "$ArtifactDir\run.log"
```

PowerShell's `*>` merges all output streams (stdout, stderr, warnings, etc.)
into the file in one redirect.

### Long-running execution

Default behavior is to launch the driver as a long-running command and let the
agent return control to the user immediately. This is **not** an agent-specific
flag — it's a behavior the agent's harness has to support, expressed differently
in each tool:

- **Claude Code**: set `run_in_background: true` on the Bash tool call. The
  harness will deliver a notification when the command completes.
- **Codex / generic shell agents**: start the command in a backgrounded shell
  session and poll `<artifact_dir>/run.log` for progress. PowerShell:
  `Start-Process -FilePath tools\perf_validators\run.bat -ArgumentList @('run', $AssetAbs, '--csv', "$ArtifactDir\issues.csv", '--summary', "$ArtifactDir\summary.json") -RedirectStandardOutput "$ArtifactDir\run.log" -RedirectStandardError "$ArtifactDir\run.err" -NoNewWindow`.
  POSIX: `nohup ... &`. cmd.exe: `start /B ...`. The driver writes per-rule
  analysis results and timing lines to the log; read bounded snapshots to see
  what's running.
- **Foreground (`--foreground` / `-f`)**: just run synchronously. Allow a
  generous timeout (10+ minutes) when the harness exposes one.

After launching as a long-running command, immediately tell the user:

> Validation is running in the background for `<filename>`. I'll present the
> results when it finishes (typically 1–5 minutes for medium assets, longer
> on large or complex assets). You can ask me for a bounded status snapshot
> from `<artifact_dir>/run.log` if you want a progress update.

For status checks during a backgrounded run, show a bounded log snapshot:

```bash
tail -n 80 "$ARTIFACT_DIR/run.log"   # POSIX
```
```powershell
Get-Content "$ArtifactDir\run.log" -Tail 80   # Windows (PowerShell)
```

### Standalone Python/API path — analysis-mode fallback

When optional helper wrappers are not present, use analysis-mode operations
directly to emulate the Usd Optimize portion of the rule sweep. This does not cover the
base `usd_validation_nvidia` rule family. For the canonical Python API and the
full operation list, see `.agents/operations/INVOCATION.md` and each operation
guide's Analysis Mode section.

Write a summary JSON with this top-level shape so `interpret-validators` can
detect the fallback path:

```json
{
  "validator_path": "standalone-analysis-mode",
  "findings": {
    "<operation>": {"output": {"analysis": {}}}
  }
}
```

After the driver finishes, also stash the asset path next to the artifacts so
`interpret-validators` can confirm it later:

```bash
printf '%s\n' "$ASSET_ABS" > "$ARTIFACT_DIR/asset.txt"   # POSIX
```
```powershell
# Windows (PowerShell) — Set-Content writes the literal value, no trailing space
Set-Content -Path "$ArtifactDir\asset.txt" -Value $AssetAbs
```

## Step 4 — Print a terse summary

The driver writes by-severity / by-rule counts to `run.log` (filtered to Scene
Optimizer rules — the CSV is the unfiltered source of truth). Show the last
~40 lines of `run.log` so the user sees the headline counts, then append:

```
Validation complete.
  Artifacts: <ARTIFACT_DIR>/
    issues.csv     — all rules (base + UsdOptimize), one row per issue
    summary.json   — totals, by-severity, by-rule, validate seconds
    run.log        — full driver stdout/stderr (tailable during run)
    asset.txt      — asset path (used by interpret-validators)
  Note: the tail above shows UsdOptimize rules only.
        The CSV also contains base usd-validation-nvidia rule issues.

Run the interpret-validators skill on this asset (Claude alias:
`/interpret-validators <asset>`) for the full report and follow-ups
(e.g. "which prims are affected by …?", "how do I fix …?").
```

Don't try to interpret the issues here — that's `interpret-validators`'s job.

### Zero Scene-Optimizer issues is normal on some assets

If the run reports 0 Scene-Optimizer issues but the CSV contains base-rule
issues, that's expected for assets with no `UsdGeomMesh` prims
(references-only stages, materials libraries, layout files that only
reference geometry from elsewhere, etc.). The Scene
Optimizer base class short-circuits mesh-only rules via a `REQUIRES_MESH`
flag — see `validators/SKILL.md` §Performance behavior for the cache and
short-circuit details. The 7 hierarchy / materials / animation rules
(`UsdOptimizeDuplicateHierarchiesChecker`, `UsdOptimizeEmptyLeafChecker`,
`UsdOptimizeFlatHierarchiesChecker`, `UsdOptimizeFlattenHierarchyChecker`,
`UsdOptimizeInvisiblePrimsChecker`, `UsdOptimizeDuplicateMaterialsChecker`,
`UsdOptimizeRedundantTimeSamplesChecker`) keep running on mesh-less stages;
the rest skip silently. The authoritative list is whichever validator modules
under `source/core/python/usd_optimize/validators/` set
`REQUIRES_MESH = False`. **Don't tell the user "Usd Optimize rules failed
to register" without checking the asset for `UsdGeomMesh` content first.**

---

## Errors to handle

| Symptom | Cause | What to tell the user |
|---|---|---|
| `Build not found at _build/...` from run wrapper | `./repo.sh build` (POSIX) or `repo.bat build` (Windows) hasn't run | Point at the `build` skill: build the repo first. |
| PowerShell `& tools\perf_validators\run.bat ...` errors with `NativeCommandError` | PowerShell wraps stderr lines from native executables in error records. The driver succeeded — `*>` redirects all streams to the log; check `$LASTEXITCODE` to confirm. | Don't add `2>&1` separately; `*>` already merges. |
| Driver exits non-zero | Driver failure (USD open error, plugin import error) | Surface stderr (last lines of `run.log`); don't try to parse the partial CSV. |
| `usd-validation-nvidia` install fails inside the wrapper | First-run pip install behind a proxy | Tell the user to set `HTTPS_PROXY` / `HTTP_PROXY` and re-run. |

If the user hasn't built the repo, **don't attempt the build yourself** — the
build takes minutes and may need flags. Point at the `build` skill and stop.

## Purpose

Run the full default rule set (Usd Optimize + usd-validation-nvidia base) when
the selected runtime provides validator wrappers, or use the standalone
analysis-mode fallback for the Usd Optimize rule family when it does not. Save CSV /
summary JSON / log artifacts to a stable per-asset directory. The artifacts
are the input to `interpret-validators`. Handle input validation,
artifact-dir resolution, long-running execution, and post-run hand-off.

## Prerequisites

- A selected Usd Optimize runtime. Checkout-provided helper wrappers require a built
  repo (`./repo.sh build` or `repo.bat build`); Kit, standalone package, and
  wheel installs may not provide those wrappers.
- A USD asset (`.usd` / `.usda` / `.usdc` / `.usdz`).
- A writable `<temp>` (`$TMPDIR` / `%TEMP%` / `/tmp`) for the default
  artifact directory; override with `--logs-dir`.
- Network access for the first run — the wrapper auto-installs
  `usd-validation-nvidia` into the bundled Python on first use.

## Limitations

- This skill only **runs** validators and saves artifacts; it never
  interprets them. For the structured report and follow-up Q&A, use
  `interpret-validators`.
- Some rules, especially overlap and occlusion checks, can add minutes on
  large stages.
- The driver has no `--rule` flag — filtering is done downstream by
  `interpret-validators` after the full run.
- Long-running execution depends on the agent harness (Claude Code,
  Codex, plain shell) — see *Long-running execution* for the
  per-harness invocation pattern.
- Results from mesh-only rules are silently skipped on stages with no
  `UsdGeomMesh` (the `REQUIRES_MESH` short-circuit). That's expected,
  not a registration failure — see the *Zero Scene-Optimizer issues
  is normal on some assets* callout.

## Troubleshooting

The *Errors to handle* table above already covers the main failure
modes. Additional meta-troubleshooting:

| Symptom | Likely cause | Fix |
|---|---|---|
| `summary.json` reports 0 Usd Optimize issues but the CSV has many `Scene*` rows | The driver log filters to Usd Optimize rules; the CSV is the unfiltered source of truth. | Always interpret from the CSV via `interpret-validators` — don't rely on the run-log tail. |
| Wrapper exits immediately with `Build not found` | `_build/` missing for the current platform/config. | Run the `build` skill first; verify `_build/<platform>/release/lib/` exists. |
| Long-running command "completes" but no artifacts on disk | The driver crashed before writing — check `run.log` for stack/import errors. | Tail the log; common cause is a `libusd` mismatch when `PYTHONPATH` is shadowed. |
| Validation exceeds the agent harness timeout | Slower rules (e.g. `findOverlappingMeshes`, O(n²)) can take tens of minutes on large stages. | Use the harness's long-running path (Claude `run_in_background: true`, Codex `Start-Process` / `nohup`). |
