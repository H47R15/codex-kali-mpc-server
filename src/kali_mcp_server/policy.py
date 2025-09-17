"""Policy loading utilities for tool execution guardrails."""

from __future__ import annotations

import os
from functools import lru_cache
from importlib import resources
from pathlib import Path
from typing import Any, Dict, Optional

import yaml

DEFAULT_POLICY_FILENAME = "config/policy.yaml"
ENV_POLICY_PATH = "KALI_POLICY_FILE"
ENV_MAX_CONCURRENCY = "KALI_MAX_CONCURRENT_RUNS"
ENV_DEFAULT_TIMEOUT = "KALI_DEFAULT_TIMEOUT"


def _resolve_policy_path() -> Path:
    env_path = os.environ.get(ENV_POLICY_PATH)
    if env_path:
        return Path(env_path).expanduser().resolve()
    return Path(__file__).resolve().parents[2] / DEFAULT_POLICY_FILENAME


def _load_policy(path: Path) -> Dict[str, Any]:
    if path.exists():
        with path.open("r", encoding="utf-8") as handle:
            loaded = yaml.safe_load(handle) or {}
    else:
        default_resource = resources.files("kali_mcp_server.assets") / "policy.yaml"
        with resources.as_file(default_resource) as default_path:
            loaded = yaml.safe_load(default_path.read_text(encoding="utf-8")) or {}
    loaded.setdefault("global", {})
    loaded.setdefault("tools", {})
    return loaded


@lru_cache(maxsize=1)
def get_policy() -> Dict[str, Any]:
    path = _resolve_policy_path()
    return _load_policy(path)


def reload_policy() -> None:
    get_policy.cache_clear()
    try:
        from . import executor  # circular import safe during reload

        executor.reset_runtime_limits()
    except Exception:  # pragma: no cover - best effort
        pass


def get_global_setting(key: str, default: Optional[int] = None) -> Any:
    policy = get_policy().get("global", {})
    env_override = None
    if key == "max_concurrent_runs":
        env_override = os.environ.get(ENV_MAX_CONCURRENCY)
    elif key == "default_timeout":
        env_override = os.environ.get(ENV_DEFAULT_TIMEOUT)
    if env_override is not None:
        try:
            return int(env_override)
        except ValueError:
            return default
    return policy.get(key, default)


def get_tool_policy(tool_name: str) -> Dict[str, Any]:
    tools = get_policy().get("tools", {})
    return tools.get(tool_name.lower(), {})
