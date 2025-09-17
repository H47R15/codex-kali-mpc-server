# Kali Security MCP Server

Containerised Model Context Protocol (MCP) server that wraps a curated set of Kali Linux utilities so they can be invoked from Codex or any MCP-compatible client.

## Prerequisites

- Docker Engine with access to the daemon socket (the setup mounts `/var/run/docker.sock`).
- Codex CLI with MCP support (`codex mcp list` should work).
- A local MCP configuration folder at `~/.docker/mcp/` (created automatically the first time you run `docker mcp` commands).

## 1. Build the Kali MCP image

```bash
docker build -t kali--mcp-server .
```

> The double hyphen mirrors the image reference used in the catalog (`kali--mcp-server:latest`).

## 2. Create the custom catalog entry

Edit `~/.docker/mcp/catalogs/custom.yaml` (create the file if it does not exist) and add the Kali server block:

```yaml
version: 2
name: cbyte-mcp
displayName: Cbyte MCP Servers
registry:
  kali:
    description: "Helper utilities for Kali-based security workflows (tool lookups, CVE summaries)."
    title: "Kali Security"
    type: server
    dateAdded: "2025-01-24T00:00:00Z"
    image: kali--mcp-server:latest
    ref: ""
    readme: ""
    toolsUrl: ""
    source: ""
    upstream: ""
    icon: https://midfeed.com/fav.svg
    tools:
      - name: list_categories
      - name: describe_tool
      - name: suggest_tools
      - name: latest_cves
      - name: run_kali_tool
    secrets:
      - name: KALI_TARGET_WHITELIST
        env: KALI_TARGET_WHITELIST
        example: "192.168.1.,10.0.0."
      - name: KALI_MAX_SCAN_TIME
        env: KALI_MAX_SCAN_TIME
        example: "300"
    metadata:
      category: monitoring
      tags:
        - security
        - pentesting
        - vulnerability
        - scanning
        - kali
      license: MIT
      owner: local
```

## 3. Register the catalog with Docker MCP

Ensure the global registry knows about the new `kali` entry by updating `~/.docker/mcp/registry.yaml`:

```yaml
registry:
  docker:
    ref: ""
  mcp-discord:
    ref: ""
  redis:
    ref: ""
  kali:
    ref: ""
```

If the file already exists, just add the `kali` block under `registry`.

## 4. (Optional) Provision secrets

Set any secrets referenced in the catalog before the gateway launches:

```bash
docker mcp secret set KALI_MAX_SCAN_TIME="300"
```

Repeat for `KALI_TARGET_WHITELIST` or additional values as needed.

## 5. Register the gateway with Codex

Use Codex to run the official Docker MCP gateway container, mounting the catalog and registry you just edited:

```bash
codex mcp add MCP_DOCKER_TOOL -- docker run -i --rm \
  -v /var/run/docker.sock:/var/run/docker.sock \
  -v /Users/cbyte/.docker/mcp:/mcp \
  docker/mcp-gateway \
  --catalog=/mcp/catalogs/docker-mcp.yaml \
  --catalog=/mcp/catalogs/custom.yaml \
  --config=/mcp/config.yaml \
  --registry=/mcp/registry.yaml \
  --tools-config=/mcp/tools.yaml \
  --transport=stdio
```

Replace `/Users/cbyte/.docker/mcp` with your actual MCP configuration directory if different.

## 6. Verify the server

List the MCP servers and confirm `kali` appears:

```bash
codex mcp list
```

You can also exercise the server directly with the MCP inspector:

```bash
npx @modelcontextprotocol/inspector docker run -i --rm \
  -v /var/run/docker.sock:/var/run/docker.sock \
  -v /Users/cbyte/.docker/mcp:/mcp \
  docker/mcp-gateway \
  --catalog=/mcp/catalogs/custom.yaml \
  --registry=/mcp/registry.yaml \
  --transport=stdio
```

## Local development with Poetry

- Install dependencies: `poetry install`
- Launch the MCP server locally: `poetry run python kali_server.py`
- Export requirements for Docker builds: `poetry export --without-hashes -f requirements.txt -o requirements.txt`

The Docker image consumes `requirements.txt`, so re-run the export whenever you add or upgrade dependencies via Poetry.

## Available tools

- `list_categories` – list curated Kali tool groupings.
- `describe_tool` – surface category and summary for a specific tool.
- `suggest_tools` – locate tools that match a free-form task description.
- `latest_cves` – fetch the newest matching CVEs from the NVD API.
- `run_kali_tool` – execute select Kali binaries (`aircrack-ng`, `nmap`, `theHarvester`, `dnsenum`, `nikto`, `sqlmap`) inside the container and return stdout/stderr.

## Release workflow

Semantic-release automates versioning and changelog updates using Conventional Commits.

- Install dependencies once: `npm install` (Node.js 18+ recommended).
- Dry-run locally: `npx semantic-release --no-ci --dry-run`.
- Real release (typically executed in CI): `npx semantic-release`.

The configuration lives in `.releaserc.json`, and generated notes land in `CHANGELOG.md`.
