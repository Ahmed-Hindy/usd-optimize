# SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#

"""Smoke-test an extracted or archived Windows prebuilt Usd Optimize package.

The checks are intentionally executed in subprocesses. This keeps a native crash
in one import or plugin-loading path from preventing the script from reporting
which smoke step failed.
"""

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

        stage = Usd.Stage.CreateInMemory()
        assert stage
        print("pxr import and in-memory stage creation succeeded")
    """,
    "core_import": """
        from usd_optimize.core import ExecutionContext, UsdOptimizeCore

        context = ExecutionContext()
        assert context.usdStageId == -1
        assert UsdOptimizeCore.getInstance()
        print("usd_optimize.core import succeeded")
    """,
    "operation_registry": """
        from usd_optimize.core import UsdOptimizeCore

        core = UsdOptimizeCore.getInstance()
        operations = core.getOperations()
        assert len(operations) > 0, "operation registry is empty"
        print(f"operation registry contains {len(operations)} operations")
    """,
    "standalone_import": """
        from usd_optimize.core.scripts import standalone

        assert standalone.execute_commands_from_json
        print("public standalone API import succeeded")
    """,
    "standalone_execute": """
        import json

        from pxr import Usd, UsdGeom
        from usd_optimize.core.scripts import standalone

        stage = Usd.Stage.CreateInMemory()
        UsdGeom.Xform.Define(stage, "/World")
        UsdGeom.Cube.Define(stage, "/World/keep")
        UsdGeom.Cube.Define(stage, "/World/delete_me")
        operations_json = json.dumps([
            {"operation": "executionContext", "verbose": False},
            {"operation": "deletePrims", "primPaths": ["/World/delete_me"]},
        ])

        assert standalone.execute_commands_from_json(stage, operations_json)
        assert stage.GetPrimAtPath("/World/keep")
        assert not stage.GetPrimAtPath("/World/delete_me")
        print("standalone JSON execution succeeded")
    """,
}

EXTERNAL_FIXTURE_CHECK = """
    import os
    from pathlib import Path

    from pxr import Usd

    fixture_path = Path(os.environ["USD_OPTIMIZE_EXTERNAL_FIXTURE_USD"])
    stage = Usd.Stage.Open(str(fixture_path))
    assert stage, f"failed to open fixture USD: {fixture_path}"
    assert stage.GetPrimAtPath("/hello/world"), "fixture is missing /hello/world"
    print(f"external USD fixture opened successfully: {fixture_path}")
"""


DLL_DIRECTORIES = ("lib", "extraLibs", "lib/operations")
PYTHON_DIRECTORIES = ("python", "usdpy")


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--package-archive", type=Path, help="Path to a usd_optimize prebuilt package zip.")
    parser.add_argument("--package-root", type=Path, help="Path to an already extracted prebuilt package root.")
    parser.add_argument(
        "--packages-dir", type=Path, default=Path("_build/packages"), help="Directory to search for package zips."
    )
    parser.add_argument(
        "--external-fixture-usd",
        type=Path,
        help="Optional file-backed USD fixture to open through the packaged runtime.",
    )
    parser.add_argument(
        "--keep-extracted",
        action="store_true",
        help="Keep temporary extraction directory after the run.",
    )
    return parser.parse_args()


def find_package_archive(packages_dir: Path) -> Path:
    """Find the shipping prebuilt package archive in a package output directory.

    Args:
        packages_dir: Directory containing package archives.

    Returns:
        The newest matching package archive.

    Raises:
        FileNotFoundError: If no shipping prebuilt package archive is found.
    """
    candidates = []
    for archive_path in packages_dir.glob("usd_optimize_*.zip"):
        name = archive_path.name
        if name.startswith("usd_optimize_tests_"):
            continue
        candidates.append(archive_path)

    if not candidates:
        raise FileNotFoundError(f"No usd_optimize_*.zip package archive found in {packages_dir}")

    return max(candidates, key=lambda archive_path: archive_path.stat().st_mtime)


def extract_package_archive(package_archive: Path, extract_root: Path) -> Path:
    """Extract a package archive and return the package root directory.

    Args:
        package_archive: Zip archive produced by ``repo.bat package``.
        extract_root: Temporary directory to extract into.

    Returns:
        The extracted package root directory.
    """
    with zipfile.ZipFile(package_archive) as package_zip:
        package_zip.extractall(extract_root)

    child_directories = [path for path in extract_root.iterdir() if path.is_dir()]
    if len(child_directories) == 1 and (child_directories[0] / "python").exists():
        return child_directories[0]
    return extract_root


def validate_package_root(package_root: Path) -> list[str]:
    """Validate package root structure without importing native modules.

    Args:
        package_root: Extracted package root.

    Returns:
        A list of validation error messages.
    """
    required_directories = ("python", "usdpy", "lib", "extraLibs")
    required_files = (
        "python/usd_optimize/bootstrap.py",
        "python/usd_optimize/core/scripts/standalone.py",
    )

    missing_directories = [name for name in required_directories if not (package_root / name).exists()]
    missing_files = [name for name in required_files if not (package_root / name).is_file()]

    errors = [f"Missing package directory: {name}" for name in missing_directories]
    errors.extend(f"Missing package file: {name}" for name in missing_files)
    return errors


def make_subprocess_environment(package_root: Path, external_fixture_usd: Path | None = None) -> dict[str, str]:
    """Create an isolated environment for package smoke subprocesses.

    Args:
        package_root: Extracted package root.
        external_fixture_usd: Optional file-backed USD fixture to smoke-test.

    Returns:
        Environment variables for a smoke subprocess.
    """
    environment = os.environ.copy()
    python_paths = [str(package_root / directory) for directory in PYTHON_DIRECTORIES]
    path_entries = [
        str(package_root / directory) for directory in DLL_DIRECTORIES if (package_root / directory).exists()
    ]

    existing_python_path = environment.get("PYTHONPATH")
    if existing_python_path:
        python_paths.append(existing_python_path)

    environment["PYTHONPATH"] = os.pathsep.join(python_paths)
    environment["PATH"] = os.pathsep.join(path_entries + [environment.get("PATH", "")])
    environment["PYTHONUTF8"] = "1"
    environment["USD_OPTIMIZE_PACKAGE_ROOT"] = str(package_root)
    if external_fixture_usd:
        environment["USD_OPTIMIZE_EXTERNAL_FIXTURE_USD"] = str(external_fixture_usd)
    return environment


def build_check_code(check_body: str) -> str:
    """Build Python code for a smoke check subprocess.

    Args:
        check_body: Python code body for the check.

    Returns:
        Complete Python code including runtime bootstrap configuration.
    """
    bootstrap_code = """
import os

from usd_optimize.bootstrap import configure_runtime

configure_runtime(os.environ["USD_OPTIMIZE_PACKAGE_ROOT"])
"""
    return "\n".join((textwrap.dedent(bootstrap_code).strip(), textwrap.dedent(check_body).strip(), ""))


def run_check(check_name: str, check_body: str, environment: dict[str, str]) -> bool:
    """Run one smoke check in a subprocess.

    Args:
        check_name: Human-readable check name.
        check_body: Python code body for the check.
        environment: Environment variables for the subprocess.

    Returns:
        ``True`` if the check exits successfully, otherwise ``False``.
    """
    print(f"\n=== {check_name} ===", flush=True)
    process = subprocess.run(
        [sys.executable, "-c", build_check_code(check_body)],
        env=environment,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
    )
    print(process.stdout.rstrip(), flush=True)
    if process.returncode != 0:
        print(f"FAILED: {check_name} exited with code {process.returncode}", flush=True)
        return False
    print(f"PASSED: {check_name}", flush=True)
    return True


def main() -> int:
    """Run package smoke checks."""
    args = parse_args()

    temporary_directory = None
    if args.package_root:
        package_root = args.package_root.resolve()
    else:
        package_archive = args.package_archive or find_package_archive(args.packages_dir)
        temporary_directory = Path(tempfile.mkdtemp(prefix="usd_optimize_smoke_"))
        package_root = extract_package_archive(package_archive.resolve(), temporary_directory)
        print(f"Extracted {package_archive} to {package_root}", flush=True)

    try:
        errors = validate_package_root(package_root)
        if errors:
            for error in errors:
                print(error, flush=True)
            return 1

        external_fixture_usd = args.external_fixture_usd.resolve() if args.external_fixture_usd else None
        if external_fixture_usd and not external_fixture_usd.is_file():
            print(f"Missing external USD fixture: {external_fixture_usd}", flush=True)
            return 1

        environment = make_subprocess_environment(package_root, external_fixture_usd)
        print(f"Package root: {package_root}", flush=True)
        print(f"Python executable: {sys.executable}", flush=True)
        print(f"PYTHONPATH: {environment['PYTHONPATH']}", flush=True)
        if external_fixture_usd:
            print(f"External USD fixture: {external_fixture_usd}", flush=True)

        checks = dict(CHECKS)
        if external_fixture_usd:
            checks["external_fixture_open"] = EXTERNAL_FIXTURE_CHECK

        success = True
        for check_name, check_body in checks.items():
            success = run_check(check_name, check_body, environment) and success
        return 0 if success else 1
    finally:
        if temporary_directory and not args.keep_extracted:
            shutil.rmtree(temporary_directory, ignore_errors=True)


if __name__ == "__main__":
    raise SystemExit(main())
