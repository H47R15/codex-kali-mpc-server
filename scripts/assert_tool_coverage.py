#!/usr/bin/env python3
"""Validate that the generated Kali tool dataset covers all meta-package categories."""

from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path
from typing import Optional, Sequence, Set

REPO_ROOT = Path(__file__).resolve().parents[1]
DATASET_PATH = REPO_ROOT / "data" / "kali_tools.json"
META_PACKAGE_PREFIX = "kali-tools-"


def run_command(cmd: Sequence[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        cmd,
        check=True,
        capture_output=True,
        text=True,
    )


def discover_meta_packages() -> Set[str]:
    cmd = ["apt-cache", "--no-generate", "pkgnames", META_PACKAGE_PREFIX]
    try:
        result = run_command(cmd)
    except (FileNotFoundError, subprocess.CalledProcessError):
        return set()
    return {line.strip() for line in result.stdout.splitlines() if line.strip()}


def load_dataset(path: Path) -> Set[str]:
    data = json.loads(path.read_text())
    packages = set()
    for entry in data:
        package = entry.get("package", "")
        if package.startswith(META_PACKAGE_PREFIX):
            packages.add(package)
    return packages


def parse_args(argv: Optional[Sequence[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--dataset",
        type=Path,
        default=DATASET_PATH,
        help=f"Path to kali_tools.json (default: {DATASET_PATH})",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Fail the check when apt-cache probing is unavailable.",
    )
    return parser.parse_args(argv)


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = parse_args(argv)
    expected = discover_meta_packages()
    if not expected:
        if args.strict:
            print("Unable to query apt-cache for kali-tools-* packages", flush=True)
            return 1
        print("Warning: apt-cache unavailable; skipping coverage diff.", flush=True)
        return 0

    observed = load_dataset(args.dataset)
    missing = sorted(expected - observed)
    extra = sorted(observed - expected)

    if missing:
        print("Missing packages:")
        for package in missing:
            print(f"  - {package}")
    if extra:
        print("Unexpected packages in dataset:")
        for package in extra:
            print(f"  - {package}")

    if missing or extra:
        return 2

    print("Dataset covers all discovered kali-tools-* packages.")
    return 0


if __name__ == "__main__":  # pragma: no cover - CLI behaviour
    raise SystemExit(main())
