# Catalog Reference

This document explains how the Kali Security MCP server metadata is structured when
submitting to the Docker MCP registry.

## Files

| Path | Purpose |
| --- | --- |
| `docker/server.yaml` | Registry entry that links the container image, readme, and tool manifest. |
| `docker/tools.json` | Machine-readable description of exposed MCP tools (names, docs, arguments). |
| `data/kali_tools.json` | Generated dataset that lists every Kali binary surfaced by the server. |
| `config/policy.yaml` | Execution guardrails (flag allowlists, timeouts, target confirmation). |

## `docker/server.yaml`

Key fields to keep up to date before opening a registry pull request:

- `image`: The Docker image reference you intend to publish (e.g., `ghcr.io/<org>/kali-mcp-server:latest`).
- `transport`: Always `stdio` for this server.
- `catalog.readme`: Points at `README.md` so the registry renders the local documentation.
- `catalog.tools`: Reference to `docker/tools.json`.
- `secrets` / `env`: Mirror the runtime requirements in the README (currently empty because the
  policy file and dataset live inside the image).

## `docker/tools.json`

Each tool entry contains:

- `name`: Matches the MCP method exposed by `FastMCP`.
- `description`: One-line summary rendered in registry UIs.
- `arguments`: Array describing the positional arguments. Use `type: string`/`integer` to help the
  registry produce better forms.

The manifest already includes dataset-aware helpers (`list_tools`, `search_tools`,
`run_kali_tool`, `run_kali_tool_stream`, `export_run_history`). Update the descriptions whenever you
add or remove flags or parameters from the server implementation.

## Dataset & Policy

The runtime depends on both the dataset and policy files:

- Run `python scripts/sync_tools.py --csv-output data/kali_tools.csv` inside the container to refresh
  the dataset. This updates `data/kali_tools.json`, the optional CSV mirror, and the README coverage block.
- Edit `config/policy.yaml` to adjust execution guardrails. The server allows overriding at runtime via
  `KALI_POLICY_FILE`, `KALI_MAX_CONCURRENT_RUNS`, `KALI_DEFAULT_TIMEOUT`, and `KALI_TARGET_WHITELIST`.

When preparing a registry submission, verify that the dataset, policy, and catalog all reference the same
set of tools and that the README instructions match the container behaviour.
