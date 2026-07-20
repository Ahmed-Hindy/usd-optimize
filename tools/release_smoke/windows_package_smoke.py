# SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0

"""Smoke-test a Windows Usd Optimize prebuilt package in isolated subprocesses."""

from __future__ import annotations

import argparse
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import textwrap
import zipfile


CHECKS = {
    "pxr_import": """
        from pxr import Usd

        assert Usd.Stage.CreateInMemory()
        print("pxr import and in-memory stage creation succeeded")
    """,
    "core_registry": """
        from usd_optimize.core import UsdOptimizeCore

        operations = UsdOptimizeCore.getInstance().getOperations()
        assert "findOverlappingMeshes" in operations, operations
        print(f"operation registry contains {len(operations)} operations")
    """,
    "execute_config": """
        from pxr import Usd, UsdGeom
        from usd_optimize.core import ExecutionContext, UsdOptimizeCore

        stage = Usd.Stage.CreateInMemory()
        UsdGeom.Xform.Define(stage, "/World")
        UsdGeom.Cube.Define(stage, "/World/keep")
        UsdGeom.Cube.Define(stage, "/World/delete_me")
        context = ExecutionContext()
        assert context.set_stage(stage)
        results = UsdOptimizeCore.getInstance().executeConfig(
            context,
            [{"operation": "deletePrims", "primPaths": ["/World/delete_me"]}],
        )
        assert all(success for success, _error, _output in results), results
        assert stage.GetPrimAtPath("/World/keep")
        assert not stage.GetPrimAtPath("/World/delete_me")
        print("UsdOptimizeCore.executeConfig succeeded")
    """,
    "find_overlapping_meshes": """
        import os

        from pxr import Usd
        from usd_optimize.core import ExecutionContext, UsdOptimizeCore

        stage = Usd.Stage.Open(os.environ["USD_OPTIMIZE_OVERLAP_FIXTURE"])
        assert stage, os.environ["USD_OPTIMIZE_OVERLAP_FIXTURE"]
        context = ExecutionContext()
        assert context.set_stage(stage)
        context.analysisMode = 1
        results = UsdOptimizeCore.getInstance().executeConfig(
            context,
            [{
                "operation": "findOverlappingMeshes",
                "paths": [],
                "reportIslands": False,
                "fullStageReport": False,
                "useGpu": False,
            }],
        )
        assert len(results) == 1, results
        success, error, output = results[0]
        assert success, (error, output)
        assert output.get("analysis", {}).get("suppressedOverlaps") == 8, output
        print("findOverlappingMeshes CPU analysis returned suppressedOverlaps=8")
    """,
}


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments.

    Returns:
        Parsed command-line arguments.
    """
    parser = argparse.ArgumentParser(description=__doc__)
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--package-archive", type=Path, help="Released package ZIP archive.")
    source.add_argument("--package-root", type=Path, help="Already extracted package root.")
    parser.add_argument(
        "--overlap-fixture-usd",
        type=Path,
        required=True,
        help="USD fixture with the expected eight CPU overlap findings.",
    )
    parser.add_argument(
        "--keep-extracted",
        action="store_true",
        help="Keep a temporary archive extraction for inspection.",
    )
    return parser.parse_args()


def extract_archive(archive_path: Path, destination: Path) -> Path:
    """Extract a package archive and locate its package root.

    Args:
        archive_path: ZIP archive to extract.
        destination: Empty directory receiving extracted files.

    Returns:
        The directory containing the package layout.
    """
    with zipfile.ZipFile(archive_path) as archive:
        archive.extractall(destination)

    children = [path for path in destination.iterdir() if path.is_dir()]
    if len(children) == 1 and (children[0] / "python").is_dir():
        return children[0]
    return destination


def validate_package_root(package_root: Path) -> list[str]:
    """Return structural errors for an extracted Windows package.

    Args:
        package_root: Extracted package root directory.

    Returns:
        Human-readable structural errors. An empty list means the expected
        v1.1-era package layout is present.
    """
    expected_paths = (
        "python/usd_optimize/core/__init__.py",
        "usdpy/pxr",
        "lib/usd_optimize.core.dll",
        "extraLibs",
        "lib/operations/findOverlappingMeshes.dll",
    )
    return [f"Missing package path: {path}" for path in expected_paths if not (package_root / path).exists()]


def make_environment(package_root: Path, overlap_fixture: Path) -> dict[str, str]:
    """Create a clean child-process environment for package loading.

    Args:
        package_root: Extracted package root directory.
        overlap_fixture: USD fixture for the targeted overlap check.

    Returns:
        Environment values for Python and CLI smoke subprocesses.
    """
    environment = os.environ.copy()
    python_paths = [str(package_root / "python"), str(package_root / "usdpy")]
    existing_python_path = environment.get("PYTHONPATH")
    if existing_python_path:
        python_paths.append(existing_python_path)
    environment["PYTHONPATH"] = os.pathsep.join(python_paths)
    environment["PATH"] = os.pathsep.join(
        [str(package_root / "lib"), str(package_root / "extraLibs"), environment.get("PATH", "")]
    )
    environment["PYTHONUTF8"] = "1"
    environment["USD_OPTIMIZE_OVERLAP_FIXTURE"] = str(overlap_fixture)
    return environment


def run_python_check(name: str, source: str, environment: dict[str, str]) -> bool:
    """Run one Python check in a new process.

    Args:
        name: Human-readable check name.
        source: Python source code to execute.
        environment: Package-configured child-process environment.

    Returns:
        ``True`` only when the subprocess exits successfully.
    """
    print(f"\n=== {name} ===", flush=True)
    process = subprocess.run(
        [sys.executable, "-c", textwrap.dedent(source)],
        env=environment,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
    )
    print(process.stdout.rstrip(), flush=True)
    if process.returncode:
        print(f"FAILED: {name} exited with code {process.returncode}", flush=True)
        return False
    print(f"PASSED: {name}", flush=True)
    return True


def run_cli_check(package_root: Path, overlap_fixture: Path, environment: dict[str, str]) -> bool:
    """Run the packaged CLI against the targeted overlap fixture.

    Args:
        package_root: Extracted package root directory.
        overlap_fixture: USD fixture with known overlap results.
        environment: Package-configured child-process environment.

    Returns:
        ``True`` only when the CLI exits successfully.
    """
    executable = package_root / "bin" / "usdOptimize.exe"
    if not executable.is_file():
        print("\nSKIPPED: packaged_cli_find_overlapping_meshes (CLI is not shipped in this package)", flush=True)
        return True

    print("\n=== packaged_cli_find_overlapping_meshes ===", flush=True)
    command = [
        str(executable),
        "--input",
        str(overlap_fixture),
        "--analysis",
        "--operation",
        "findOverlappingMeshes",
        "--argument",
        "useGpu=0",
    ]
    process = subprocess.run(
        command,
        env=environment,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
    )
    print(process.stdout.rstrip(), flush=True)
    if process.returncode:
        print(f"FAILED: packaged_cli_find_overlapping_meshes exited with code {process.returncode}", flush=True)
        return False
    print("PASSED: packaged_cli_find_overlapping_meshes", flush=True)
    return True


def main() -> int:
    """Run the Windows package smoke suite.

    Returns:
        Process exit status.
    """
    args = parse_args()
    fixture = args.overlap_fixture_usd.resolve()
    if not fixture.is_file():
        print(f"Missing overlap fixture: {fixture}", flush=True)
        return 1

    temporary_directory = None
    if args.package_root:
        package_root = args.package_root.resolve()
    else:
        archive = args.package_archive.resolve()
        if not archive.is_file():
            print(f"Missing package archive: {archive}", flush=True)
            return 1
        temporary_directory = Path(tempfile.mkdtemp(prefix="usd_optimize_release_smoke_"))
        package_root = extract_archive(archive, temporary_directory)

    try:
        errors = validate_package_root(package_root)
        if errors:
            print("\n".join(errors), flush=True)
            return 1

        print(f"Package root: {package_root}", flush=True)
        print(f"Python executable: {sys.executable}", flush=True)
        environment = make_environment(package_root, fixture)
        results = [run_python_check(name, source, environment) for name, source in CHECKS.items()]
        results.append(run_cli_check(package_root, fixture, environment))
        return 0 if all(results) else 1
    finally:
        if temporary_directory and not args.keep_extracted:
            shutil.rmtree(temporary_directory, ignore_errors=True)


if __name__ == "__main__":
    raise SystemExit(main())
