# Preparing a Docker MCP Registry Submission

This guide distills the [official contributing process](https://github.com/docker/mcp-registry/blob/main/CONTRIBUTING.md) into Kali-specific steps so we can publish the server to Docker's catalog quickly.

## Prerequisites
- Go 1.24+, Docker Desktop, and the Task CLI (`brew install go-task/tap/go-task`).
- Access to this repository and permission to push a feature branch on the fork of [`docker/mcp-registry`](https://github.com/docker/mcp-registry).

## 1. Generate the server entry
1. Clone your fork of `docker/mcp-registry` and `cd` into it.
2. Copy `docker/server.yaml` and `docker/tools.json` from this repo into `servers/kali-security/` inside the registry fork. The folder name must match the `name` field.
3. Run the Task wizard to validate the metadata and adjust anything Docker-specific:
   ```bash
   task wizard
   ```
   Use `https://github.com/H47R15/codex-kali-mpc-server` as the project URL, keep the `security` category, and confirm the optional secrets listed in our template.

## 2. Build and inspect locally
Run the local validation helpers before opening a pull request:
```bash
python scripts/validate_registry_manifest.py
task build -- --tools kali-security
task catalog -- kali-security
docker mcp catalog import $PWD/catalogs/kali-security/catalog.yaml
```
This will build (or validate) the container and create a catalog entry that can be tested through Docker Desktop's MCP Toolkit. When you're done testing, clean up with `docker mcp catalog reset`.

## 3. Open the pull request
- Commit the new `servers/kali-security` folder (including `server.yaml` and `tools.json`).
- Confirm CI jobs pass in your fork.
- Use a descriptive PR title (e.g., `Add Kali Security MCP server`) and describe the testing commands you ran.
- Respond to reviewer feedback promptly; Docker will squash-merge after approval.

## Troubleshooting tips
- If `task build -- --tools kali-security` fails because the server needs configuration, recheck `tools.json` syntax—the build falls back to this file instead of auto-discovering tools.
- Ensure the env list in `server.yaml` matches the runtime knobs in `src/kali_mcp_server/executor.py`/`policy.py` (e.g., `KALI_TOOL_DATA`, `KALI_POLICY_FILE`, `KALI_TARGET_WHITELIST`, `KALI_MAX_CONCURRENT_RUNS`, `KALI_DEFAULT_TIMEOUT`).
