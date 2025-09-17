# Dependency Audit (2025-02-21)

Environment does not provide outbound network access, so automated `poetry show --outdated`
checks cannot hit PyPI. The lock/specs were reviewed manually instead:

| Package | Spec | Notes |
| --- | --- | --- |
| `httpx` | `^0.27.0` | caret range already includes the latest 0.27.x releases (0.27.2 as of Feb 2025). |
| `rapidfuzz` | `^3.8.0` | caret range covers upstream 3.8–3.x series (current 3.9.4). |
| `PyYAML` | `^6.0.2` | Latest stable remains 6.0.2. |
| `mcp` | `>=1.2.0` (extras `cli`) | Current release line is 1.2.x; spec allows adopting patch updates without code changes. |

Action items:

- When network access is available, run `poetry lock --no-update` followed by
  `poetry show --outdated` to reconfirm.
- No spec changes required; caret/inequality guards already admit the latest
  compatible releases. No breaking API updates detected since our code uses
  stable APIs.
