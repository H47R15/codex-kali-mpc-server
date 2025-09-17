# Repository Guidelines

## Project Structure & Module Organization
Core server logic lives in `kali_server.py`, exposing the FastMCP tool set. Python packaging metadata (`pyproject.toml`) and lock exports (`requirements.txt`) sit at the root to keep Docker builds deterministic. Release automation is isolated in `package.json`, while operational metadata (`registry.yaml`, `Dockerfile`, helper scripts like `macOs.sh`) reside alongside `README.md` for quick operator handoff. Add new modules under the root or a future `kali_server/` package, and mirror tests under `tests/` with matching relative paths.

## Build, Test, and Development Commands
Run `poetry install` to create the virtualenv. Start the server locally with `poetry run python kali_server.py`; it binds the MCP tools without Docker. Build and tag the container via `docker build -t ghcr.io/h47r15/kali-mcp-server:latest .` before publishing to registries. Regenerate dependency pins for Docker by running `poetry export --without-hashes -f requirements.txt -o requirements.txt`. Release notes are produced with `npm run semantic-release -- --no-ci --dry-run` (check locally) or without the flag when cutting an actual release.

## Coding Style & Naming Conventions
Target Python 3.11+ and follow PEP 8 with 4-space indentation. Keep module-level constants UPPER_SNAKE_CASE, coroutine functions in snake_case, and favor descriptive tool names (e.g., `suggest_tools`). Type hints and concise docstrings, as used in `kali_server.py`, are required for new public APIs. Maintain structured logging through the shared `logger` instance instead of ad-hoc prints.

## Testing Guidelines
Use `pytest` (already configured via Poetry) and place suites under `tests/` named `test_<feature>.py`. Aim to cover new tool handlers and error branches; mock outbound HTTP requests with `httpx`'s `MockTransport` or similar fixtures. Run `poetry run pytest` before proposing changes, and include regression cases when modifying CLI contracts or schema definitions.

## Commit & Pull Request Guidelines
Follow Conventional Commits (`docs:`, `chore:`, `feat:`) as reflected in the existing history. Group related edits per commit, keep subject lines under 72 characters, and describe the behavior change in the body when needed. Pull requests should link to tracking issues, outline testing performed, and include command outputs for releases or Docker changes. Attach screenshots only when UI-facing artifacts are impacted; otherwise share logs or sample tool responses.

## Task Tracking & Additional Tasks Discovery
Keep `TODO.md` synchronized with active work. After completing a planned task, tick its checkbox so backlog status stays accurate. If an unplanned need surfaces mid-work, capture it under the "Additional Tasks Discovery" section in `TODO.md` and leave the box unchecked until it is scheduled. Offer a short context line (e.g., "Investigate new CVE backlog triage script") so triage is quick for the next contributor.

## Security & Configuration Tips
Document any new runtime knobs in `README.md` and the MCP catalog, mirroring existing entries for `KALI_TARGET_WHITELIST`, `KALI_POLICY_FILE`, and related environment variables. Never hard-code credentials; rely on environment variables surfaced via Docker secrets. When adding external calls, validate responses and enforce conservative timeouts to protect the MCP gateway from hanging invocations.
