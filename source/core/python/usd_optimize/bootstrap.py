# SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#

"""Runtime bootstrap helpers for standalone Usd Optimize packages."""

from __future__ import annotations

from dataclasses import dataclass
import os
from pathlib import Path
import sys
from typing import Any, Dict, List, Optional, Sequence

_CONFIGURED_DLL_DIRECTORIES: Dict[str, Any] = {}


@dataclass(frozen=True)
class RuntimeConfig:
    """Resolved runtime paths for a standalone Usd Optimize package.

    Attributes:
        package_root: Root directory of the extracted package.
        python_paths: Python import directories added to ``sys.path``.
        dll_directories: Runtime library directories added to ``PATH`` and,
            on Windows, registered with ``os.add_dll_directory``.
    """

    package_root: Path
    python_paths: List[Path]
    dll_directories: List[Path]


def configure_runtime(package_root: Optional[os.PathLike] = None) -> RuntimeConfig:
    """Configure Python and native-library search paths for a package.

    This function is intended for standalone/prebuilt package consumers. It is
    safe to call more than once. On Windows, it keeps ``os.add_dll_directory``
    handles alive for the process lifetime so extension modules and operation
    plugins can resolve transitive DLL dependencies reliably.

    Args:
        package_root: Root directory of the extracted package. If omitted, the
            root is inferred from this module's location in a prebuilt package.

    Returns:
        The resolved runtime configuration.

    Raises:
        FileNotFoundError: If the package root does not exist.
    """
    resolved_package_root = _resolve_package_root(package_root)
    if not resolved_package_root.exists():
        raise FileNotFoundError(f"Package root does not exist: {resolved_package_root}")

    python_paths = _existing_directories(resolved_package_root, ("python", "usdpy"))
    dll_directories = _existing_directories(
        resolved_package_root,
        ("lib", "extraLibs", os.path.join("lib", "operations")),
    )

    _prepend_sys_paths(python_paths)
    _prepend_environment_paths("PYTHONPATH", python_paths)
    _prepend_environment_paths("PATH", dll_directories)
    _configure_windows_dll_directories(dll_directories)

    return RuntimeConfig(
        package_root=resolved_package_root,
        python_paths=python_paths,
        dll_directories=dll_directories,
    )


def _resolve_package_root(package_root: Optional[os.PathLike]) -> Path:
    """Resolve the package root from an explicit path or this file location."""
    if package_root is not None:
        return Path(package_root).expanduser().resolve()

    # In a prebuilt package this file lives at:
    #   <package_root>/python/usd_optimize/bootstrap.py
    return Path(__file__).resolve().parents[2]


def _existing_directories(package_root: Path, relative_paths: Sequence[str]) -> List[Path]:
    """Return existing package directories for the given relative paths."""
    directories = []
    for relative_path in relative_paths:
        directory = (package_root / relative_path).resolve()
        if directory.exists():
            directories.append(directory)
    return directories


def _prepend_sys_paths(paths: Sequence[Path]) -> None:
    """Prepend paths to ``sys.path`` without creating duplicates."""
    existing_paths = {_normalize_path_for_compare(Path(path)) for path in sys.path if path}
    for path in reversed(paths):
        normalized_path = _normalize_path_for_compare(path)
        if normalized_path not in existing_paths:
            sys.path.insert(0, str(path))
            existing_paths.add(normalized_path)


def _prepend_environment_paths(variable_name: str, paths: Sequence[Path]) -> None:
    """Prepend filesystem paths to an environment variable without duplicates."""
    existing_value = os.environ.get(variable_name, "")
    existing_parts = [part for part in existing_value.split(os.pathsep) if part]
    normalized_existing_parts = {_normalize_path_for_compare(Path(part)) for part in existing_parts}

    new_parts = []
    for path in paths:
        normalized_path = _normalize_path_for_compare(path)
        if normalized_path not in normalized_existing_parts:
            new_parts.append(str(path))
            normalized_existing_parts.add(normalized_path)

    if new_parts:
        os.environ[variable_name] = os.pathsep.join(new_parts + existing_parts)


def _configure_windows_dll_directories(dll_directories: Sequence[Path]) -> None:
    """Register DLL directories on Windows and keep directory handles alive."""
    add_dll_directory = getattr(os, "add_dll_directory", None)
    if add_dll_directory is None:
        return

    for directory in dll_directories:
        directory_key = _normalize_path_for_compare(directory)
        if directory_key not in _CONFIGURED_DLL_DIRECTORIES:
            _CONFIGURED_DLL_DIRECTORIES[directory_key] = add_dll_directory(str(directory))


def _normalize_path_for_compare(path: Path) -> str:
    """Normalize a path for duplicate detection."""
    normalized_path = str(path.expanduser().resolve())
    if os.name == "nt":
        return normalized_path.casefold()
    return normalized_path
