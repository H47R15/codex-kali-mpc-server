"""Runtime helpers for executing Kali tools inside the container."""

from __future__ import annotations

import asyncio
import os
import shlex
from collections import deque
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Deque, Dict, Iterable, List, Optional, Tuple

from .dataset import Tool, ToolDataset, get_dataset
from .policy import get_global_setting, get_policy, get_tool_policy

try:  # pragma: no cover - platform specific
    import resource as _resource
except ImportError:  # pragma: no cover - non-Unix platforms
    _resource = None

DEFAULT_TIMEOUT_SECONDS = 60.0
RUN_HISTORY_LIMIT = 100
RUN_HISTORY: Deque[Dict[str, object]] = deque(maxlen=RUN_HISTORY_LIMIT)
_RUN_SEMAPHORE: Optional[asyncio.Semaphore] = None


def get_run_history() -> List[Dict[str, object]]:
    """Return a snapshot of recent tool executions."""
    return list(RUN_HISTORY)


def _record_run(entry: Dict[str, object]) -> None:
    RUN_HISTORY.append(
        {
            **entry,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
    )


def reset_runtime_limits() -> None:
    """Reset cached concurrency controls (used when policy changes)."""
    global _RUN_SEMAPHORE
    _RUN_SEMAPHORE = None


def _get_semaphore() -> asyncio.Semaphore:
    global _RUN_SEMAPHORE
    if _RUN_SEMAPHORE is None:
        max_runs = get_global_setting("max_concurrent_runs", 1) or 1
        _RUN_SEMAPHORE = asyncio.Semaphore(max(1, int(max_runs)))
    return _RUN_SEMAPHORE


@dataclass
class ExecutionPlan:
    tool: Tool
    command: List[str]
    timeout: float
    resource_limits: Dict[str, float]


def _parse_arguments(arguments: str) -> List[str]:
    if not arguments.strip():
        return []
    return shlex.split(arguments)


def _targets_from_args(args: Iterable[str]) -> List[str]:
    return [arg for arg in args if arg and not arg.startswith("-")]


def _validate_targets(policy: Dict[str, object], args: List[str]) -> Optional[str]:
    prefixes = policy.get("target_prefix_whitelist", []) or []
    env_whitelist = os.environ.get("KALI_TARGET_WHITELIST", "")
    if env_whitelist:
        prefixes = list(prefixes) + [item.strip() for item in env_whitelist.split(",") if item.strip()]
    targets = _targets_from_args(args)
    if not targets:
        return "Error: Provide at least one target for this command."
    if not prefixes:
        return "Error: Target confirmation required but no whitelist configured." \
            " Set `KALI_TARGET_WHITELIST` or update policy."
    for target in targets:
        if not any(target.startswith(prefix) for prefix in prefixes):
            return f"Error: Target '{target}' is not permitted by the whitelist."
    return None


def _resolve_execution(
    tool_name: str,
    arguments: str,
    requested_timeout: float,
    dataset: ToolDataset,
) -> Tuple[Optional[ExecutionPlan], Optional[str]]:
    if not tool_name.strip():
        return None, "Error: Provide the tool_name parameter."

    tool = dataset.get(tool_name)
    if not tool:
        suggestions = dataset.fuzzy_search(tool_name, limit=5)
        if suggestions:
            lines = [f"Error: Unknown tool '{tool_name}'. Suggestions:"]
            lines.extend(f"- {suggestion.name}" for suggestion in suggestions)
            return None, "\n".join(lines)
        return None, f"Error: Unknown tool '{tool_name}'."

    policy = get_tool_policy(tool.name)
    global_policy = get_policy().get("global", {})

    try:
        extra_args: List[str] = _parse_arguments(arguments)
    except ValueError as exc:  # pragma: no cover - defensive parsing
        return None, f"Error: Unable to parse arguments ({exc})."

    if not extra_args and tool.default_args:
        extra_args = _parse_arguments(tool.default_args)

    allowed_flags = set(policy.get("allowed_flags", []) or [])
    if allowed_flags:
        for token in extra_args:
            if token.startswith("-") and token not in allowed_flags:
                return None, (
                    f"Error: Flag '{token}' is not permitted for '{tool.name}'. Allowed: "
                    + ", ".join(sorted(allowed_flags))
                )

    if policy.get("requires_target_confirmation"):
        error = _validate_targets(policy, extra_args)
        if error:
            return None, error

    binary = tool.binary_path
    if not binary:
        return None, f"Error: Execution for '{tool.name}' is not enabled in this container."

    policy_timeout = policy.get("default_timeout")
    global_default = get_global_setting("default_timeout", DEFAULT_TIMEOUT_SECONDS)
    timeout = requested_timeout or policy_timeout or global_default or DEFAULT_TIMEOUT_SECONDS
    timeout = float(timeout)
    max_timeout = policy.get("max_timeout")
    if max_timeout:
        timeout = min(timeout, float(max_timeout))

    resource_limits = _compute_resource_limits(global_policy, policy)

    return (
        ExecutionPlan(
            tool=tool,
            command=[binary, *extra_args],
            timeout=timeout,
            resource_limits=resource_limits,
        ),
        None,
    )


def _compute_resource_limits(
    global_policy: Dict[str, object], tool_policy: Dict[str, object]
) -> Dict[str, float]:
    limits: Dict[str, float] = {}
    global_limits = (global_policy or {}).get("resource_limits", {}) or {}
    tool_limits = tool_policy.get("resource_limits", {}) or {}
    for key in ("cpu_time_limit", "memory_limit_mb"):
        value = tool_limits.get(key, global_limits.get(key))
        if value is not None:
            try:
                limits[key] = float(value)
            except (TypeError, ValueError):
                continue
    return limits


def _build_preexec_fn(resource_limits: Dict[str, float]):
    if not resource_limits or _resource is None:
        return None

    cpu_limit = resource_limits.get("cpu_time_limit")
    mem_limit = resource_limits.get("memory_limit_mb")
    if not cpu_limit and not mem_limit:
        return None

    def _limit_resources():  # pragma: no cover - executed in child process
        if cpu_limit:
            seconds = max(1, int(cpu_limit))
            try:
                _resource.setrlimit(_resource.RLIMIT_CPU, (seconds, seconds))
            except (ValueError, OSError):
                pass
        if mem_limit:
            bytes_limit = max(1, int(mem_limit)) * 1024 * 1024
            try:
                _resource.setrlimit(
                    _resource.RLIMIT_AS,
                    (bytes_limit, bytes_limit),
                )
            except (AttributeError, ValueError, OSError):
                pass

    return _limit_resources


async def run_tool(
    tool_name: str,
    arguments: str = "",
    timeout: float = DEFAULT_TIMEOUT_SECONDS,
    dataset: Optional[ToolDataset] = None,
) -> str:
    """Execute a Kali tool and capture stdout/stderr."""
    dataset = dataset or get_dataset()
    plan, error = _resolve_execution(tool_name, arguments, timeout, dataset)
    if error:
        return error
    assert plan is not None  # for type checkers

    semaphore = _get_semaphore()
    start = datetime.now(timezone.utc)
    async with semaphore:
        try:
            process = await asyncio.create_subprocess_exec(
                *plan.command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                preexec_fn=_build_preexec_fn(plan.resource_limits),
            )
        except FileNotFoundError:  # pragma: no cover - defensive
            return f"Error: Executable '{plan.command[0]}' not found inside the container."

        try:
            stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=plan.timeout)
        except asyncio.TimeoutError:
            process.kill()
            await process.communicate()
            _record_run(
                {
                    "tool": plan.tool.name,
                    "arguments": arguments,
                    "exit_code": "timeout",
                    "mode": "batch",
                }
            )
            return f"Error: Tool execution timed out after {int(plan.timeout)} seconds."

    duration = (datetime.now(timezone.utc) - start).total_seconds()
    _record_run(
        {
            "tool": plan.tool.name,
            "arguments": arguments,
            "exit_code": process.returncode,
            "duration": duration,
            "mode": "batch",
        }
    )

    output_lines = [
        f"Command: {' '.join(plan.command)}",
        f"Exit code: {process.returncode}",
        "--- stdout ---",
        stdout.decode("utf-8", errors="replace") or "<no output>",
        "--- stderr ---",
        stderr.decode("utf-8", errors="replace") or "<no output>",
    ]
    return "\n".join(output_lines)


async def stream_tool(
    tool_name: str,
    arguments: str = "",
    timeout: float = DEFAULT_TIMEOUT_SECONDS,
    dataset: Optional[ToolDataset] = None,
):
    """Async generator that streams tool output line-by-line."""
    dataset = dataset or get_dataset()
    plan, error = _resolve_execution(tool_name, arguments, timeout, dataset)
    if error:
        yield error
        return
    assert plan is not None

    semaphore = _get_semaphore()
    start = datetime.now(timezone.utc)
    async with semaphore:
        try:
            process = await asyncio.create_subprocess_exec(
                *plan.command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                preexec_fn=_build_preexec_fn(plan.resource_limits),
            )
        except FileNotFoundError:
            yield f"Error: Executable '{plan.command[0]}' not found inside the container."
            return

        queue: asyncio.Queue[Optional[str]] = asyncio.Queue()

        async def pump(reader: asyncio.StreamReader, label: str) -> None:
            try:
                while True:
                    chunk = await reader.readline()
                    if not chunk:
                        break
                    await queue.put(f"[{label}] {chunk.decode('utf-8', errors='replace').rstrip()}")
            finally:
                await queue.put(None)

        tasks = [
            asyncio.create_task(pump(process.stdout, "stdout")),
            asyncio.create_task(pump(process.stderr, "stderr")),
        ]

        completed_streams = 0
        try:
            while completed_streams < len(tasks):
                try:
                    item = await asyncio.wait_for(queue.get(), timeout=plan.timeout)
                except asyncio.TimeoutError:
                    process.kill()
                    await process.communicate()
                    for task in tasks:
                        task.cancel()
                    _record_run(
                        {
                            "tool": plan.tool.name,
                            "arguments": arguments,
                            "exit_code": "timeout",
                            "mode": "stream",
                        }
                    )
                    yield f"Error: Tool execution timed out after {int(plan.timeout)} seconds."
                    return
                if item is None:
                    completed_streams += 1
                    continue
                yield item
            returncode = await asyncio.wait_for(process.wait(), timeout=1)
        finally:
            for task in tasks:
                task.cancel()

    duration = (datetime.now(timezone.utc) - start).total_seconds()
    _record_run(
        {
            "tool": plan.tool.name,
            "arguments": arguments,
            "exit_code": returncode,
            "duration": duration,
            "mode": "stream",
        }
    )
    yield f"[meta] exit_code={returncode}"
