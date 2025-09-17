#!/usr/bin/env bash

set -euo pipefail

log() {
  printf '[macOs.sh] %s\n' "$1"
}

command_exists() {
  command -v "$1" >/dev/null 2>&1
}

if ! command_exists brew; then
  printf 'Homebrew is required but not installed.\n' >&2
  exit 1
fi

if ! command_exists codex; then
  log 'Installing Codex CLI via Homebrew (tap warp-labs/codex)...'
  brew tap warp-labs/codex >/dev/null 2>&1 || true
  brew install warp-labs/codex/codex || brew install codex
else
  log 'Codex CLI already installed.'
fi

if ! command_exists docker; then
  log 'Installing Docker Desktop via Homebrew cask...'
  brew install --cask docker
  log 'Docker Desktop installed. Launch it once manually to finalise setup.'
else
  log 'Docker CLI already present.'
fi

if ! command_exists poetry; then
  log 'Installing Poetry via Homebrew...'
  brew install poetry
else
  log 'Poetry already installed.'
fi

MCP_DIR="${HOME}/.docker/mcp"
CATALOG_DIR="${MCP_DIR}/catalogs"
CUSTOM_CATALOG="${CATALOG_DIR}/custom.yaml"
REGISTRY_FILE="${MCP_DIR}/registry.yaml"

log "Ensuring MCP directories exist at ${MCP_DIR}..."
mkdir -p "${CATALOG_DIR}"

timestamp=$(date +%Y%m%d%H%M%S)

if [ -f "${CUSTOM_CATALOG}" ]; then
  log "Backing up existing custom catalog to ${CUSTOM_CATALOG}.bak.${timestamp}"
  cp "${CUSTOM_CATALOG}" "${CUSTOM_CATALOG}.bak.${timestamp}"
fi

log 'Writing Kali entry to custom catalog...'
cat <<'YAML' >"${CUSTOM_CATALOG}"
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
YAML

if [ -f "${REGISTRY_FILE}" ]; then
  log "Backing up existing registry to ${REGISTRY_FILE}.bak.${timestamp}"
  cp "${REGISTRY_FILE}" "${REGISTRY_FILE}.bak.${timestamp}"
fi

if ! [ -f "${REGISTRY_FILE}" ]; then
  cat <<'YAML' >"${REGISTRY_FILE}"
registry:
  docker:
    ref: ""
  mcp-discord:
    ref: ""
  redis:
    ref: ""
  kali:
    ref: ""
YAML
else
  if grep -q '^  kali:' "${REGISTRY_FILE}"; then
    log 'Kali entry already present in registry; leaving file unchanged.'
  else
    if grep -q '^registry:' "${REGISTRY_FILE}"; then
      log 'Appending Kali entry to existing registry file.'
      printf '  kali:\n    ref: ""\n' >> "${REGISTRY_FILE}"
    else
      log 'Registry file missing root node; rewriting with Kali entry.'
      cat <<'YAML' >"${REGISTRY_FILE}"
registry:
  kali:
    ref: ""
YAML
    fi
  fi
fi

if ! command_exists codex; then
  printf 'Codex CLI not available after installation attempt; skipping registration.\n' >&2
  exit 1
fi

GATEWAY_NAME="MCP_DOCKER_TOOL"
log 'Registering Docker MCP gateway with Codex...'
codex mcp add "${GATEWAY_NAME}" -- docker run -i --rm \
  -v /var/run/docker.sock:/var/run/docker.sock \
  -v "${MCP_DIR}":/mcp \
  docker/mcp-gateway \
  --catalog=/mcp/catalogs/docker-mcp.yaml \
  --catalog=/mcp/catalogs/custom.yaml \
  --config=/mcp/config.yaml \
  --registry=/mcp/registry.yaml \
  --tools-config=/mcp/tools.yaml \
  --transport=stdio

log 'Setup complete. Run `codex mcp list` to verify the new gateway.'
