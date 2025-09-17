#!/usr/bin/env python3
"""Kali Security MCP server exposing helper utilities for common security workflows."""

import asyncio
import logging
import shlex
import sys
from datetime import datetime, timezone
from typing import Dict, Tuple

import httpx
from mcp.server.fastmcp import FastMCP

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    stream=sys.stderr,
)
logger = logging.getLogger("kali-security-server")

mcp = FastMCP("kali-security")

KALI_TOOL_LIBRARY: Dict[str, Dict[str, str]] = {
    "information gathering": {
        "nmap": "Network scanner used for host discovery and port auditing.",
        "theharvester": "Open source intelligence gathering tool for emails, subdomains, and names.",
        "dnsenum": "Performs DNS enumeration to discover hosts and records.",
    },
    "vulnerability analysis": {
        "nikto": "Web server scanner that tests for over 6700 potentially dangerous files and programs.",
        "openvas": "Full-featured vulnerability scanner with scheduled scan support.",
        "sqlmap": "Automates detection and exploitation of SQL injection flaws.",
    },
    "wireless attacks": {
        "aircrack-ng": "Suite for capturing and cracking Wi-Fi network keys.",
        "reaver": "Implements brute force attack against Wi-Fi Protected Setup.",
        "cowpatty": "Performs dictionary attacks against WPA-PSK networks.",
    },
    "exploitation": {
        "metasploit-framework": "Collection of exploit modules, payloads, and post-exploitation tools.",
        "beef": "Browser exploitation framework focused on client-side attacks.",
        "searchsploit": "Command-line search utility for Exploit-DB advisories.",
    },
    "post exploitation": {
        "mimikatz": "Extracts credentials and performs post-exploitation tricks on Windows.",
        "empire": "PowerShell and Python post-exploitation agent.",
        "crackmapexec": "Swiss army knife for pentesting Windows/Active Directory environments.",
    },
}

# Map friendly tool names to the executable that ships in the Kali image.
KALI_TOOL_BINARIES = {
    "aircrack-ng": "aircrack-ng",
    "nmap": "nmap",
    "theharvester": "theHarvester",
    "dnsenum": "dnsenum",
    "nikto": "nikto",
    "sqlmap": "sqlmap",
}


def _normalize(text: str) -> str:
    """Normalize free-form text for lookup."""
    return text.strip().lower()


def _find_tool(tool_name: str) -> Tuple[str, str]:
    """Return category and description for a known tool."""
    normalized = _normalize(tool_name)
    for category, tools in KALI_TOOL_LIBRARY.items():
        for name, description in tools.items():
            if normalized in {name.lower(), name.replace("-", " ").lower()}:
                return category, description
    raise KeyError(f"Unknown tool: {tool_name}")


@mcp.tool()
async def list_categories() -> str:
    """List available Kali tool categories."""
    categories = sorted(KALI_TOOL_LIBRARY)
    lines = ["Available Kali tool categories:"]
    lines.extend(f"- {category.title()}" for category in categories)
    return "\n".join(lines)


@mcp.tool()
async def describe_tool(tool_name: str = "") -> str:
    """Describe a Kali tool and show its category."""
    if not tool_name.strip():
        return "Error: Provide the tool_name parameter."
    try:
        category, description = _find_tool(tool_name)
    except KeyError as exc:
        logger.warning(str(exc))
        return f"Error: {exc}."
    lines = [
        f"Tool: {tool_name.strip()}",
        f"Category: {category.title()}",
        f"Details: {description}",
    ]
    return "\n".join(lines)


@mcp.tool()
async def suggest_tools(task: str = "") -> str:
    """Suggest Kali tools for the supplied task description."""
    if not task.strip():
        return "Error: Provide the task parameter."
    normalized_task = _normalize(task)
    matches = []
    for category, tools in KALI_TOOL_LIBRARY.items():
        for name, description in tools.items():
            search_blob = " ".join(
                [name.lower(), description.lower(), category.lower()]
            )
            if all(token in search_blob for token in normalized_task.split() if token):
                matches.append((name, category, description))
    if not matches:
        return (
            f"No direct matches found for '{task}'. Try using more specific keywords."
        )
    lines = [f"Suggested tools for '{task}':"]
    for name, category, description in matches[:5]:
        lines.append(f"- {name} ({category}): {description}")
    if len(matches) > 5:
        lines.append(f"Showing 5 of {len(matches)} matches.")
    return "\n".join(lines)


@mcp.tool()
async def latest_cves(keyword: str = "") -> str:
    """Fetch recent CVE summaries from NVD matching a keyword."""
    if not keyword.strip():
        return "Error: Provide the keyword parameter."
    params = {
        "keywordSearch": keyword.strip(),
        "resultsPerPage": 3,
        "startIndex": 0,
    }
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(
                "https://services.nvd.nist.gov/rest/json/cves/2.0",
                params=params,
            )
            response.raise_for_status()
            payload = response.json()
    except httpx.HTTPStatusError as exc:
        logger.error("NVD status error: %s", exc)
        return f"Error: NVD returned HTTP {exc.response.status_code}."
    except httpx.RequestError as exc:
        logger.error("NVD request failure: %s", exc)
        return "Error: Unable to reach the NVD service."
    vulnerabilities = payload.get("vulnerabilities", [])
    if not vulnerabilities:
        return f"No CVEs found for '{keyword}'."
    lines = [f"Latest CVEs mentioning '{keyword}':"]
    for item in vulnerabilities:
        cve_data = item.get("cve", {})
        cve_id = cve_data.get("id", "Unknown CVE")
        descriptions = cve_data.get("descriptions", [])
        summary = (
            descriptions[0].get("value", "No summary provided")
            if descriptions
            else "No summary provided"
        )
        published = cve_data.get("published", "")
        published_at = "unknown"
        if published:
            try:
                published_dt = datetime.fromisoformat(published.replace("Z", "+00:00"))
                published_at = published_dt.astimezone(timezone.utc).strftime(
                    "%Y-%m-%d"
                )
            except ValueError:
                published_at = published[:10]
        lines.append(f"- {cve_id} ({published_at}): {summary}")
    return "\n".join(lines)


@mcp.tool()
async def run_kali_tool(tool_name: str = "", arguments: str = "") -> str:
    """Execute a Kali tool inside the container and return its output."""
    if not tool_name.strip():
        return "Error: Provide the tool_name parameter."

    normalized = _normalize(tool_name)
    # Find the canonical tool name first so we can surface category errors nicely.
    try:
        category, _ = _find_tool(tool_name)
    except KeyError as exc:
        logger.warning("Execution rejected for unknown tool: %s", tool_name)
        return f"Error: {exc}."

    binary = KALI_TOOL_BINARIES.get(normalized)
    if not binary:
        return (
            f"Error: Execution for '{tool_name}' is not enabled in this container."
        )

    # Build the command safely using shlex splitting for additional arguments.
    try:
        extra_args = shlex.split(arguments)
    except ValueError as exc:
        return f"Error: Unable to parse arguments ({exc})."

    cmd = [binary, *extra_args]
    logger.info("Running tool '%s' (%s) with args: %s", tool_name, category, extra_args)

    try:
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=60.0)
    except FileNotFoundError:
        return f"Error: Executable '{binary}' not found inside the container."
    except asyncio.TimeoutError:
        process.kill()
        await process.communicate()
        return "Error: Tool execution timed out after 60 seconds."

    output_lines = [
        f"Command: {' '.join(cmd)}",
        f"Exit code: {process.returncode}",
        "--- stdout ---",
        stdout.decode("utf-8", errors="replace") or "<no output>",
        "--- stderr ---",
        stderr.decode("utf-8", errors="replace") or "<no output>",
    ]
    return "\n".join(output_lines)


# === SERVER STARTUP ===
if __name__ == "__main__":
    logger.info("Starting Kali Security MCP server...")
    try:
        mcp.run(transport="stdio")
    except Exception as exc:  # pragma: no cover - startup failures
        logger.error("Server error: %s", exc, exc_info=True)
        sys.exit(1)
