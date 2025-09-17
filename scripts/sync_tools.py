#!/usr/bin/env python3
"""Synchronise the Kali tool metadata dataset.

This script is intended to run inside the Kali MCP container where `apt` and
`dpkg-query` have access to the Kali package repositories. When those tools are
unavailable (for example, during local development on macOS), it falls back to a
minimal dataset derived from the in-repo catalog so developers can still
exercise the code paths that consume the data.
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import shutil
import subprocess
import sys
from collections import Counter
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Sequence

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_PATH = REPO_ROOT / "src"
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

import importlib

try:
    catalog = importlib.import_module("kali_mcp_server.catalog")  # type: ignore
except Exception:  # pragma: no cover - fallback import failure
    catalog = None  # type: ignore

DEFAULT_OUTPUT = REPO_ROOT / "data" / "kali_tools.json"
READ_ME_PATH = REPO_ROOT / "README.md"

META_PACKAGE_PREFIX = "kali-tools-"
CORE_META_PACKAGES = [
    "kali-tools-top10",
    "kali-tools-web",
    "kali-tools-information-gathering",
    "kali-tools-wireless",
    "kali-tools-bluetooth",
    "kali-tools-sniffing-spoofing",
    "kali-tools-social-engineering",
    "kali-tools-exploitation",
    "kali-tools-fuzzing",
    "kali-tools-stress",
    "kali-tools-reverse-engineering",
    "kali-tools-hardware",
    "kali-tools-sdr",
    "kali-tools-vehicle",
    "kali-tools-voip",
    "kali-tools-forensics",
    "kali-tools-crypto-stego",
    "kali-tools-maintaining-access",
    "kali-tools-reporting",
    "kali-tools-passwords",
    "kali-tools-database",
]

CATEGORY_OVERRIDES: Dict[str, str] = {
    "kali-tools-top10": "Top 10",
    "kali-tools-web": "Web Applications",
    "kali-tools-information-gathering": "Information Gathering",
    "kali-tools-wireless": "Wireless Attacks",
    "kali-tools-bluetooth": "Bluetooth",
    "kali-tools-sniffing-spoofing": "Sniffing & Spoofing",
    "kali-tools-social-engineering": "Social Engineering",
    "kali-tools-exploitation": "Exploitation",
    "kali-tools-fuzzing": "Fuzzing",
    "kali-tools-stress": "Stress Testing",
    "kali-tools-reverse-engineering": "Reverse Engineering",
    "kali-tools-hardware": "Hardware Hacking",
    "kali-tools-sdr": "Radio / SDR",
    "kali-tools-vehicle": "Vehicle Security",
    "kali-tools-voip": "VoIP",
    "kali-tools-forensics": "Forensics",
    "kali-tools-crypto-stego": "Crypto & Stego",
    "kali-tools-maintaining-access": "Maintaining Access",
    "kali-tools-reporting": "Reporting",
    "kali-tools-passwords": "Password Attacks",
    "kali-tools-database": "Database Assessment",
}

README_MARKER_START = "<!-- tool-coverage-start -->"
README_MARKER_END = "<!-- tool-coverage-end -->"


@dataclass
class ToolRecord:
    name: str
    package: str
    category: str
    summary: str
    binary_path: str
    default_args: str = ""

    def to_dict(self) -> Dict[str, str]:
        return {
            "name": self.name,
            "package": self.package,
            "category": self.category,
            "summary": self.summary,
            "binary_path": self.binary_path,
            "default_args": self.default_args,
        }


def run_command(cmd: Sequence[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        cmd,
        check=True,
        capture_output=True,
        text=True,
    )


def discover_meta_packages() -> List[str]:
    cmd = ["apt-cache", "--no-generate", "pkgnames", META_PACKAGE_PREFIX]
    try:
        result = run_command(cmd)
        packages = sorted({line.strip() for line in result.stdout.splitlines() if line.strip()})
        if packages:
            return packages
    except (subprocess.CalledProcessError, FileNotFoundError):  # pragma: no cover - system dependent
        pass
    # Fall back to the curated list if apt-cache is unavailable.
    return CORE_META_PACKAGES


def parse_description(package: str) -> str:
    cmd = ["apt-cache", "show", package]
    try:
        result = run_command(cmd)
    except (subprocess.CalledProcessError, FileNotFoundError):  # pragma: no cover - system dependent
        return "Kali meta-package"
    description_lines = []
    capture = False
    for line in result.stdout.splitlines():
        if line.startswith("Description:"):
            capture = True
            description_lines.append(line.partition(":")[2].strip())
            continue
        if capture:
            if line.startswith(" "):
                description_lines.append(line.strip())
            else:
                break
    summary = " ".join(description_lines).strip()
    return summary or "Kali meta-package"


def derive_category(package: str) -> str:
    if package in CATEGORY_OVERRIDES:
        return CATEGORY_OVERRIDES[package]
    if package.startswith(META_PACKAGE_PREFIX):
        slug = package[len(META_PACKAGE_PREFIX) :].replace("-", " ")
        return slug.title()
    return package


def iter_package_binaries(package: str) -> Iterable[Path]:
    cmd = ["dpkg-query", "-L", package]
    try:
        result = run_command(cmd)
    except (subprocess.CalledProcessError, FileNotFoundError):  # pragma: no cover - system dependent
        return []
    paths = []
    for line in result.stdout.splitlines():
        candidate = Path(line.strip())
        if not candidate.is_absolute():
            continue
        if candidate.is_symlink():
            try:
                resolved = candidate.resolve(strict=True)
            except FileNotFoundError:
                continue
            candidate = resolved
        if candidate.is_file() and os.access(candidate, os.X_OK):
            paths.append(candidate)
    return paths


def build_dataset_from_system(packages: Iterable[str]) -> List[ToolRecord]:
    dataset: List[ToolRecord] = []
    for package in packages:
        category = derive_category(package)
        summary = parse_description(package)
        for binary_path in iter_package_binaries(package):
            dataset.append(
                ToolRecord(
                    name=binary_path.name,
                    package=package,
                    category=category,
                    summary=summary,
                    binary_path=str(binary_path),
                )
            )
    return dataset


def build_dataset_from_catalog() -> List[ToolRecord]:
    if catalog is None:
        raise RuntimeError(
            "Fallback dataset requested but kali_mcp_server.catalog could not be imported"
        )
    dataset: List[ToolRecord] = []
    for category, tools in catalog.KALI_TOOL_LIBRARY.items():
        for name, description in tools.items():
            binary = catalog.KALI_TOOL_BINARIES.get(catalog.normalize(name), name)
            dataset.append(
                ToolRecord(
                    name=binary,
                    package="kali-tools-sample",
                    category=category.title(),
                    summary=description,
                    binary_path=f"/usr/bin/{binary}",
                )
            )
    return dataset


def ensure_output_dir(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


def serialize_dataset(
    dataset: List[ToolRecord], output_path: Path, csv_path: Optional[Path] = None
) -> None:
    ensure_output_dir(output_path)
    data = [record.to_dict() for record in dataset]
    output_path.write_text(
        json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    if csv_path is not None:
        ensure_output_dir(csv_path)
        with csv_path.open("w", newline="", encoding="utf-8") as handle:
            if data:
                fieldnames = list(data[0].keys())
            else:
                fieldnames = ["name", "package", "category", "summary", "binary_path", "default_args"]
            writer = csv.DictWriter(handle, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(data)


def compute_metrics(dataset: List[ToolRecord]) -> Dict[str, object]:
    category_counts = Counter(record.category for record in dataset)
    return {
        "total_tools": len(dataset),
        "category_counts": dict(sorted(category_counts.items())),
    }


def render_readme_block(metrics: Dict[str, object]) -> str:
    total = metrics["total_tools"]
    category_counts: Dict[str, int] = metrics["category_counts"]  # type: ignore[assignment]
    generated_at = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    lines = [
        README_MARKER_START,
        f"**Kali tool dataset summary** — generated {generated_at}",
        f"Total binaries tracked: {total}",
        "",
        "| Category | Tool count |",
        "| --- | ---: |",
    ]
    for category, count in category_counts.items():
        lines.append(f"| {category} | {count} |")
    lines.append(README_MARKER_END)
    return "\n".join(lines) + "\n"


def update_readme(metrics: Dict[str, object]) -> None:
    block = render_readme_block(metrics)
    if not READ_ME_PATH.exists():  # pragma: no cover - defensive
        return
    content = READ_ME_PATH.read_text(encoding="utf-8")
    if README_MARKER_START in content and README_MARKER_END in content:
        start = content.index(README_MARKER_START)
        end = content.index(README_MARKER_END) + len(README_MARKER_END)
        new_content = content[:start] + block + content[end:]
    else:
        new_content = content.rstrip() + "\n\n" + block
    READ_ME_PATH.write_text(new_content, encoding="utf-8")


def parse_args(argv: Optional[Sequence[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT,
        help=f"Path to write the dataset (default: {DEFAULT_OUTPUT})",
    )
    parser.add_argument(
        "--skip-readme",
        action="store_true",
        help="Do not update the README coverage block.",
    )
    parser.add_argument(
        "--fallback-only",
        action="store_true",
        help="Skip apt/dpkg probing and generate the fallback dataset immediately.",
    )
    parser.add_argument(
        "--csv-output",
        type=Path,
        default=None,
        help="Optional path to also write the dataset as CSV.",
    )
    return parser.parse_args(argv)


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = parse_args(argv)

    if args.fallback_only:
        dataset = build_dataset_from_catalog()
    else:
        packages = discover_meta_packages()
        dataset = build_dataset_from_system(packages)
        if not dataset:
            dataset = build_dataset_from_catalog()

    serialize_dataset(dataset, args.output, args.csv_output)
    metrics = compute_metrics(dataset)

    if not args.skip_readme:
        update_readme(metrics)

    packaged_dataset = REPO_ROOT / "src" / "kali_mcp_server" / "assets" / "kali_tools.json"
    try:
        shutil.copy2(args.output, packaged_dataset)
    except FileNotFoundError:
        pass

    print(json.dumps({"output": str(args.output), **metrics}, indent=2))
    return 0


if __name__ == "__main__":  # pragma: no cover - CLI behaviour
    raise SystemExit(main())
