# SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#

"""Download and verify external USD assets for CI smoke tests."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import shutil
import tempfile
import urllib.request


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--manifest",
        type=Path,
        default=Path("tools/windows_prebuilt_repro/external_usd_assets.json"),
        help="External asset manifest JSON file.",
    )
    parser.add_argument(
        "--assets-dir",
        type=Path,
        default=Path(".cache/usd-assets"),
        help="Directory where external assets are cached.",
    )
    parser.add_argument("--timeout", type=int, default=60, help="Download timeout per asset in seconds.")
    return parser.parse_args()


def load_manifest(manifest_path: Path) -> dict:
    """Load an external asset manifest.

    Args:
        manifest_path: Path to the JSON manifest.

    Returns:
        Parsed manifest dictionary.
    """
    with manifest_path.open("r", encoding="utf-8") as manifest_file:
        return json.load(manifest_file)


def hash_file(file_path: Path) -> str:
    """Return the SHA-256 digest for a file.

    Args:
        file_path: File to hash.

    Returns:
        Lowercase hexadecimal SHA-256 digest.
    """
    digest = hashlib.sha256()
    with file_path.open("rb") as asset_file:
        for chunk in iter(lambda: asset_file.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def download_asset(url: str, destination_path: Path, timeout: int) -> None:
    """Download a URL to a destination path via a temporary file.

    Args:
        url: Source URL to download.
        destination_path: Final destination path.
        timeout: URL open timeout in seconds.
    """
    destination_path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(delete=False, dir=str(destination_path.parent)) as temporary_file:
        temporary_path = Path(temporary_file.name)
        with urllib.request.urlopen(url, timeout=timeout) as response:
            shutil.copyfileobj(response, temporary_file)
    temporary_path.replace(destination_path)


def ensure_asset(asset: dict, assets_dir: Path, timeout: int) -> Path:
    """Download an asset if needed and verify its SHA-256 digest.

    Args:
        asset: Manifest entry describing one asset.
        assets_dir: Root directory for cached external assets.
        timeout: Download timeout per asset in seconds.

    Returns:
        Local cached asset path.

    Raises:
        RuntimeError: If the downloaded or cached file hash does not match.
    """
    relative_path = Path(asset["relative_path"])
    asset_path = assets_dir / relative_path
    expected_hash = asset["sha256"].lower()

    if asset_path.is_file() and hash_file(asset_path) == expected_hash:
        print(f"cached: {asset['name']} -> {asset_path}", flush=True)
        return asset_path

    print(f"downloading: {asset['name']} -> {asset_path}", flush=True)
    download_asset(asset["url"], asset_path, timeout)
    actual_hash = hash_file(asset_path)
    if actual_hash != expected_hash:
        asset_path.unlink(missing_ok=True)
        raise RuntimeError(
            f"SHA-256 mismatch for {asset['name']}: expected {expected_hash}, got {actual_hash}"
        )
    return asset_path


def main() -> int:
    """Download all assets in the manifest."""
    args = parse_args()
    manifest_path = args.manifest.resolve()
    assets_dir = args.assets_dir.resolve()
    manifest = load_manifest(manifest_path)

    print(f"Manifest: {manifest_path}", flush=True)
    print(f"Assets directory: {assets_dir}", flush=True)
    for asset in manifest.get("assets", []):
        ensure_asset(asset, assets_dir, args.timeout)
    print(f"External USD assets ready: {len(manifest.get('assets', []))}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
