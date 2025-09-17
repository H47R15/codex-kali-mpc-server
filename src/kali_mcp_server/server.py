"""FastMCP server wiring for the Kali tool catalog."""

from __future__ import annotations

import logging
import sys
from typing import List

from mcp.server.fastmcp import FastMCP

from .dataset import Tool, get_dataset
from .executor import get_run_history, run_tool, stream_tool
from .nvd import (
    NVDClientError,
    NVDHTTPError,
    fetch_latest_cve_summaries,
    format_cve_lines,
)

logger = logging.getLogger("kali-security-server")


def _format_tool(tool: Tool) -> str:
    lines = [
        f"Tool: {tool.name}",
        f"Category: {tool.category}",
        f"Package: {tool.package}",
        f"Binary: {tool.binary_path}",
        f"Summary: {tool.summary}",
    ]
    if tool.default_args:
        lines.append(f"Default args: {tool.default_args}")
    return "\n".join(lines)


def _format_tool_list(title: str, tools: List[Tool]) -> str:
    lines = [title]
    for tool in tools:
        lines.append(f"- {tool.name} ({tool.category}) — {tool.summary}")
    return "\n".join(lines)


def create_app() -> FastMCP:
    """Configure and return the FastMCP application."""
    app = FastMCP("kali-security")

    dataset = get_dataset()

    @app.tool()
    async def list_categories() -> str:
        """List available Kali tool categories."""
        lines = ["Available Kali tool categories:"]
        lines.extend(f"- {category}" for category in dataset.categories)
        return "\n".join(lines)

    @app.tool()
    async def list_tools(category: str = "") -> str:
        """List tools available within a category."""
        if not category.strip():
            return "Error: Provide the category parameter."
        tools = dataset.by_category(category)
        if not tools:
            return f"No tools found for category '{category}'."
        return _format_tool_list(f"Tools in category '{category}':", tools)

    @app.tool()
    async def describe_tool(tool_name: str = "") -> str:
        """Describe a Kali tool and show its category."""
        if not tool_name.strip():
            return "Error: Provide the tool_name parameter."
        tool = dataset.get(tool_name)
        if not tool:
            matches = dataset.fuzzy_search(tool_name, limit=5)
            if matches:
                suggestion_lines = ["Unknown tool. Did you mean:"]
                suggestion_lines.extend(f"- {match.name}" for match in matches)
                return "\n".join(suggestion_lines)
            return f"Error: Unknown tool '{tool_name}'."
        return _format_tool(tool)

    @app.tool()
    async def suggest_tools(task: str = "") -> str:
        """Suggest Kali tools for the supplied task description."""
        if not task.strip():
            return "Error: Provide the task parameter."
        matches = dataset.fuzzy_search(task, limit=5)
        if not matches:
            return (
                f"No direct matches found for '{task}'. Try using more specific keywords."
            )
        return _format_tool_list(f"Suggested tools for '{task}':", matches)

    @app.tool()
    async def latest_cves(keyword: str = "") -> str:
        """Fetch recent CVE summaries from NVD matching a keyword."""
        if not keyword.strip():
            return "Error: Provide the keyword parameter."
        try:
            summaries = await fetch_latest_cve_summaries(keyword.strip(), limit=3)
        except NVDHTTPError as exc:
            logger.error("NVD status error: %s", exc)
            return f"Error: NVD returned HTTP {exc.status_code}."
        except NVDClientError as exc:
            logger.error("NVD request failure: %s", exc)
            return "Error: Unable to reach the NVD service."
        return format_cve_lines(keyword, summaries)

    @app.tool()
    async def run_kali_tool(tool_name: str = "", arguments: str = "", timeout: int = 60) -> str:
        """Execute a Kali tool inside the container and return its output."""
        return await run_tool(tool_name, arguments, timeout=timeout, dataset=dataset)

    @app.stream_tool()
    async def run_kali_tool_stream(tool_name: str = "", arguments: str = "", timeout: int = 60):
        """Stream stdout/stderr from a Kali tool as it executes."""
        async for chunk in stream_tool(tool_name, arguments, timeout=timeout, dataset=dataset):
            yield chunk

    @app.tool()
    async def tool_details(tool_name: str = "") -> str:
        """Return detailed metadata about a Kali tool."""
        if not tool_name.strip():
            return "Error: Provide the tool_name parameter."
        tool = dataset.get(tool_name)
        if not tool:
            return f"Error: Unknown tool '{tool_name}'."
        return _format_tool(tool)

    @app.tool()
    async def search_tools(query: str = "", limit: int = 5) -> str:
        """Search the Kali dataset using fuzzy matching."""
        matches = dataset.fuzzy_search(query, limit=limit)
        if not matches:
            return f"No matches found for '{query}'."
        return _format_tool_list(f"Search results for '{query}':", matches)

    @app.tool()
    async def export_run_history() -> str:
        """Return recent tool execution history for auditing."""
        history = get_run_history()
        if not history:
            return "No executions recorded yet."
        lines = ["Recent executions:"]
        for entry in history:
            lines.append(
                "- {timestamp} :: {tool} :: exit={exit_code} :: args={arguments} :: mode={mode}".format(
                    **entry
                )
            )
        return "\n".join(lines)

    return app


def main() -> None:
    """Entrypoint for running the FastMCP server via `python -m kali_mcp_server`."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        stream=sys.stderr,
    )
    app = create_app()
    logger.info("Starting Kali Security MCP server...")
    try:
        app.run(transport="stdio")
    except Exception as exc:  # pragma: no cover - startup failures
        logger.error("Server error: %s", exc, exc_info=True)
        raise


if __name__ == "__main__":  # pragma: no cover - module CLI
    main()
