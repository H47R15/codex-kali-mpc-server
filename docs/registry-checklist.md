# Registry Submission Checklist

Use this worksheet when you are ready to submit the Kali Security MCP server to
Docker's MCP registry.

## 1. Prepare the registry fork
- [ ] Clone your fork of `docker/mcp-registry`.
- [ ] Copy the contents of `servers/kali-security/` from this repo into
      `servers/kali-security/` in the fork.
- [ ] Copy `docs/catalog.md` if you want an internal reference while iterating.

## 2. Validate metadata locally
- [ ] From this repository root run:
  ```bash
  python scripts/validate_registry_manifest.py
  ```
  This confirms that `docker/server.yaml`, `docker/tools.json`, and the dataset
  are mutually consistent.
- [ ] In the registry fork run the Task validations (requires the Task CLI and Docker):
  ```bash
  task build -- --tools kali-security
  task catalog -- kali-security
  docker mcp catalog import $PWD/catalogs/kali-security/catalog.yaml
  ```
  (Clean up with `docker mcp catalog reset` afterwards.)

## 3. Finalise docs and dataset
- [ ] Regenerate the dataset inside the Kali container:
  ```bash
  docker build -t ghcr.io/h47r15/kali-mcp-server:latest .
  docker run --rm -it -v "$PWD/data:/app/data" ghcr.io/h47r15/kali-mcp-server:latest \
    python scripts/sync_tools.py --csv-output data/kali_tools.csv
  ```
- [ ] Commit the updated dataset and ensure the README coverage block updates.
- [ ] Re-run `python scripts/validate_registry_manifest.py`.

## 4. Open the pull request
- [ ] Commit the new `servers/kali-security` folder in the registry fork.
- [ ] Push a branch and open a PR titled, for example, `Add Kali Security MCP server`.
- [ ] Document the validation commands you ran in the PR description.
- [ ] Respond to reviewer feedback and iterate as needed.

Keep this checklist with the project so you can reuse it on future updates.
