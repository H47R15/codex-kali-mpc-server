"""Compatibility wrapper that launches the packaged Kali MCP server."""

from __future__ import annotations

import sys
from pathlib import Path

# Allow running the script without installing the package first.
repo_root = Path(__file__).resolve().parent
src_path = repo_root / "src"
if str(src_path) not in sys.path:
    sys.path.insert(0, str(src_path))

from kali_mcp_server.server import main

if __name__ == "__main__":
    main()
