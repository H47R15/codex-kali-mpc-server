"""Kali MCP server package."""

from __future__ import annotations

from importlib import import_module
from typing import TYPE_CHECKING

__all__ = ["create_app", "main"]

if TYPE_CHECKING:  # pragma: no cover - type checkers only
    from .server import create_app as _create_app
    from .server import main as _main


def create_app():
    """Lazily import and return the FastMCP application."""
    module = import_module("kali_mcp_server.server")
    return module.create_app()


def main():
    """Entrypoint wrapper for `python -m kali_mcp_server`."""
    module = import_module("kali_mcp_server.server")
    return module.main()
