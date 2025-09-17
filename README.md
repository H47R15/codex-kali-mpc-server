# Kali Security MCP Server

Containerised Model Context Protocol (MCP) server that wraps a curated set of Kali Linux utilities so they can be invoked from Codex or any MCP-compatible client.

## Prerequisites

- Docker Engine with access to the daemon socket (the setup mounts `/var/run/docker.sock`).
- Codex CLI with MCP support (`codex mcp list` should work).
- A local MCP configuration folder at `~/.docker/mcp/` (created automatically the first time you run `docker mcp` commands).

## 1. Pull (or build) the Kali MCP image

The published container is available on GitHub Container Registry:

```bash
docker pull ghcr.io/h47r15/kali-mcp-server:latest
```

> Working on local changes? Rebuild the image with the same tag so your catalog
> keeps pointing at `ghcr.io/h47r15/kali-mcp-server:latest`:
>
> ```bash
> docker build -t ghcr.io/h47r15/kali-mcp-server:latest .
> ```

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
    image: ghcr.io/h47r15/kali-mcp-server:latest
    ref: ""
    readme: ""
    toolsUrl: ""
    source: ""
    upstream: ""
    icon: https://midfeed.com/fav.svg
    tools:
      - name: list_categories
      - name: list_tools
      - name: describe_tool
      - name: tool_details
      - name: search_tools
      - name: suggest_tools
      - name: latest_cves
      - name: run_kali_tool
      - name: run_kali_tool_stream
      - name: export_run_history
    env:
      - name: KALI_TOOL_DATA
        example: /mnt/datasets/custom_kali_tools.json
      - name: KALI_POLICY_FILE
        example: /mnt/config/policy.yaml
      - name: KALI_TARGET_WHITELIST
        example: "192.168.1.,10.0."
      - name: KALI_MAX_CONCURRENT_RUNS
        example: "2"
      - name: KALI_DEFAULT_TIMEOUT
        example: "60"
      - name: KALI_EXTRA_PATHS
        example: /opt/security/bin
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

Set environment variables (for example via Docker secrets or your shell
profile) before launching the gateway. At minimum configure
`KALI_TARGET_WHITELIST` with the CIDR prefixes you are authorised to scan.

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

## Quick local test run

Run the published container directly, mounting local dataset/policy overrides:

```bash
docker run --rm -it \
  -v "$PWD/data:/app/data" \
  -v "$PWD/config:/app/config" \
  -e KALI_TOOL_DATA=/app/data/kali_tools.json \
  -e KALI_POLICY_FILE=/app/config/policy.yaml \
  -e KALI_TARGET_WHITELIST="192.168.1.,10.0." \
  ghcr.io/h47r15/kali-mcp-server:latest \
  kali-mcp-server
```

The packaged assets under `src/kali_mcp_server/assets/` already provide defaults if
you omit the overrides; mount only the files you intend to customise.

## Local development with Poetry

- Install dependencies: `poetry install`
- Launch the MCP server locally: `poetry run python kali_server.py`
- Export requirements for Docker builds: `poetry export --without-hashes -f requirements.txt -o requirements.txt`

The Docker image consumes `requirements.txt`, so re-run the export whenever you add or upgrade dependencies via Poetry.

## Available tools

- `list_categories` – enumerate categories sourced from the generated dataset.
- `list_tools` – show every tool within a category (package, summary, binary path).
- `describe_tool` / `tool_details` – return rich metadata for a specific tool.
- `search_tools` – fuzzy match by keyword across name, summary, package, or category.
- `suggest_tools` – opinionated helper for free-form task descriptions (keyword wrapper).
- `latest_cves` – fetch the newest matching CVEs from the NVD API.
- `run_kali_tool` – execute any allow-listed Kali binary from inside the container and return stdout/stderr.
- `run_kali_tool_stream` – stream stdout/stderr in real time for long-running commands.
- `export_run_history` – retrieve recent invocation logs for auditing.

## Tool dataset workflow

- The authoritative dataset lives in `data/kali_tools.json` (with an optional CSV mirror at `data/kali_tools.csv`).
- To regenerate the dataset with the **real** Kali environment:
  1. Build the image (`docker build -t ghcr.io/h47r15/kali-mcp-server:latest .`).
  2. Launch an interactive container: `docker run --rm -it -v "$PWD/data:/app/data" ghcr.io/h47r15/kali-mcp-server:latest bash`.
  3. Inside the container run `python scripts/sync_tools.py --csv-output data/kali_tools.csv`.
  4. Commit the resulting JSON/CSV and the README coverage block will stay in sync automatically.
- For local experimentation without Docker support, use the fallback dataset (`python scripts/sync_tools.py --fallback-only`).
- Set `KALI_TOOL_DATA=/absolute/path/to/custom.json` to point the server at an alternate dataset without rebuilding the image.
- Manage execution guardrails via `config/policy.yaml` (allowed flags, timeouts, target whitelists). Override at runtime with `KALI_POLICY_FILE`, `KALI_MAX_CONCURRENT_RUNS`, `KALI_DEFAULT_TIMEOUT`, `KALI_TARGET_WHITELIST`, and `KALI_EXTRA_PATHS` (to prepend custom binaries to `PATH`).
- Meta-packages are installed opportunistically during the Docker build. If a `kali-tools-*` meta package is not available for the current architecture (for example, some sets are x86_64-only), it is skipped automatically and will not appear in the generated dataset.

## Release workflow

Semantic-release automates versioning and changelog updates using Conventional Commits.

- Install dependencies once: `npm install` (Node.js 18+ recommended).
- Dry-run locally: `npx semantic-release --no-ci --dry-run`.
- Real release (typically executed in CI): `npx semantic-release`.

The configuration lives in `.releaserc.json`, and generated notes land in `CHANGELOG.md`.

## Testing

- Install dev dependencies: `poetry install --with dev` (or `pip install -r requirements.txt && pip install -r dev-requirements.txt` if you prefer pip).
- Run unit tests: `pytest`. The suite includes mocked NVD responses via `pytest-httpx` and policy enforcement checks.
- Integration tests (optional): build and exercise the Docker image by setting `KALI_INTEGRATION=1 poetry run pytest tests/integration/test_run_tool_container.py`. To reuse a pre-built image, set `KALI_TEST_IMAGE=<registry/image:tag>`; otherwise the tests will build one locally (which can take several minutes).
- Browse usage snippets under `examples/` for quick Python and CLI helpers when testing the MCP surface locally.

## Docker MCP registry preparation

Planning to upstream this server to Docker's MCP registry? Start with the templates under `docker/` and follow `docs/docker-mcp-registry.md`, `docs/catalog.md`, and the checklist in `docs/registry-checklist.md` for the end-to-end workflow (Task CLI commands, catalog import, and PR checklist).

Before publishing:
- Refresh the dataset inside the container with `python scripts/sync_tools.py --csv-output data/kali_tools.csv`.
- Run `python scripts/validate_registry_manifest.py` to ensure `docker/server.yaml` and `docker/tools.json` stay in sync with the codebase.

<!-- tool-coverage-start -->
**Kali tool dataset summary** — generated 2025-09-17 06:37 UTC
Total binaries tracked: 15

| Category | Tool count |
| --- | ---: |
| Exploitation | 3 |
| Information Gathering | 3 |
| Post Exploitation | 3 |
| Vulnerability Analysis | 3 |
| Wireless Attacks | 3 |
<!-- tool-coverage-end -->
