"""Static metadata describing the curated Kali toolset."""

from __future__ import annotations

from typing import Dict, Iterable, Tuple

ToolLibrary = Dict[str, Dict[str, str]]

KALI_TOOL_LIBRARY: ToolLibrary = {
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


def normalize(text: str) -> str:
    """Normalize free-form text for lookup."""
    return text.strip().lower()


def iter_tools() -> Iterable[Tuple[str, str, str]]:
    """Yield (name, category, description) tuples for every known tool."""
    for category, tools in KALI_TOOL_LIBRARY.items():
        for name, description in tools.items():
            yield name, category, description


def find_tool(tool_name: str) -> Tuple[str, str]:
    """Return category and description for a known tool."""
    normalized = normalize(tool_name)
    for name, category, description in iter_tools():
        if normalized in {name.lower(), name.replace("-", " ").lower()}:
            return category, description
    raise KeyError(f"Unknown tool: {tool_name}")


def list_categories() -> Iterable[str]:
    """Return stable list of tool categories."""
    return sorted(KALI_TOOL_LIBRARY)
