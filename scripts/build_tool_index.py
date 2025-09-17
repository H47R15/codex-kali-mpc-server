"""Utility script to generate the Kali tool metadata dataset.

This is a placeholder that will be expanded in later roadmap tasks.
"""

from __future__ import annotations

import argparse
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("data/kali_tools.json"),
        help="Path to write the generated tool index.",
    )
    return parser.parse_args()


def main() -> None:  # pragma: no cover - placeholder
    args = parse_args()
    raise SystemExit(
        f"Tool index generation is not implemented yet. Intended output: {args.output}"
    )


if __name__ == "__main__":  # pragma: no cover - manual execution helper
    main()
