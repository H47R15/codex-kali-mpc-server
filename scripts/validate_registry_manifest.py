#!/usr/bin/env python3
"""Basic validation for Docker MCP registry assets."""

from __future__ import annotations

import json
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]
SERVER_PATH = REPO_ROOT / "docker" / "server.yaml"
TOOLS_PATH = REPO_ROOT / "docker" / "tools.json"
DATASET_PATH = REPO_ROOT / "data" / "kali_tools.json"


def main() -> int:
    server = yaml.safe_load(SERVER_PATH.read_text())
    tools = json.loads(TOOLS_PATH.read_text())
    dataset = json.loads(DATASET_PATH.read_text())

    tool_names = {entry["name"] for entry in tools}
    required_tools = {
        "list_categories",
        "list_tools",
        "describe_tool",
        "tool_details",
        "search_tools",
        "suggest_tools",
        "latest_cves",
        "run_kali_tool",
        "run_kali_tool_stream",
        "export_run_history",
    }
    missing_tools = sorted(required_tools - tool_names)
    if missing_tools:
        raise SystemExit(f"Missing tool definitions: {', '.join(missing_tools)}")

    dataset_tools = {entry["name"] for entry in dataset}
    if "nmap" not in dataset_tools:
        raise SystemExit("Dataset sanity check failed: nmap not found")

    env_entries = {env["name"] for env in server.get("config", {}).get("env", [])}
    expected_env = {
        "KALI_TOOL_DATA",
        "KALI_POLICY_FILE",
        "KALI_TARGET_WHITELIST",
        "KALI_MAX_CONCURRENT_RUNS",
        "KALI_DEFAULT_TIMEOUT",
        "KALI_EXTRA_PATHS",
    }
    missing_env = sorted(expected_env - env_entries)
    if missing_env:
        raise SystemExit(f"Server config missing env entries: {', '.join(missing_env)}")

    print("Registry metadata validated successfully.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
