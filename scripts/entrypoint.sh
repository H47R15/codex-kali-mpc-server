#!/usr/bin/env bash
set -euo pipefail

# Ensure standard Kali binary paths are available for the MCP runtime.
export PATH="/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin:${PATH}"
if [[ -n "${KALI_EXTRA_PATHS:-}" ]]; then
  export PATH="${KALI_EXTRA_PATHS}:${PATH}"
fi

# Default to launching the Kali MCP server if no other command is provided.
if [[ $# -eq 0 ]]; then
  set -- kali-mcp-server
fi

exec "$@"
