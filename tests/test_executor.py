import asyncio
from types import SimpleNamespace

import pytest

import kali_mcp_server.executor as executor
from kali_mcp_server.dataset import get_dataset
from kali_mcp_server import policy


@pytest.mark.asyncio
async def test_run_tool_rejects_unknown_tool():
    dataset = get_dataset()
    result = await executor.run_tool("unknown", dataset=dataset)
    assert "Unknown tool" in result


@pytest.mark.asyncio
async def test_run_tool_parses_invalid_arguments():
    dataset = get_dataset()
    result = await executor.run_tool("nmap", arguments='"unterminated', dataset=dataset)
    assert "Unable to parse arguments" in result


@pytest.mark.asyncio
async def test_run_tool_times_out(monkeypatch):
    dataset = get_dataset()

    async def fake_create_process(*_args, **_kwargs):
        async def communicate():
            await asyncio.sleep(0.01)
            return b"", b""

        return SimpleNamespace(communicate=communicate, kill=lambda: None, returncode=0)

    async def fake_wait_for(awaitable, timeout):  # pragma: no cover - helper
        closer = getattr(awaitable, "close", None)
        if callable(closer):
            closer()
        raise asyncio.TimeoutError

    monkeypatch.setattr(executor.asyncio, "create_subprocess_exec", fake_create_process)
    monkeypatch.setattr(executor.asyncio, "wait_for", fake_wait_for)

    result = await executor.run_tool(
        "nmap",
        arguments="127.0.0.1",
        timeout=0.01,
        dataset=dataset,
    )
    assert "timed out" in result


@pytest.mark.asyncio
async def test_run_tool_enforces_allowed_flags(tmp_path, monkeypatch):
    dataset = get_dataset()
    policy_path = tmp_path / "policy.yaml"
    policy_path.write_text(
        """
global:
  max_concurrent_runs: 1
tools:
  nmap:
    allowed_flags:
      - "-sV"
""",
        encoding="utf-8",
    )
    monkeypatch.setenv("KALI_POLICY_FILE", str(policy_path))
    policy.reload_policy()
    executor.reset_runtime_limits()

    result = await executor.run_tool("nmap", arguments="-A", dataset=dataset)
    assert "not permitted" in result

    monkeypatch.delenv("KALI_POLICY_FILE", raising=False)
    policy.reload_policy()
    executor.reset_runtime_limits()


@pytest.mark.asyncio
async def test_run_tool_records_history(monkeypatch):
    dataset = get_dataset()

    async def fake_create_process(*_args, **_kwargs):
        async def communicate():
            return b"done", b""

        async def wait():
            return 0

        return SimpleNamespace(
            communicate=communicate,
            kill=lambda: None,
            returncode=0,
        )

    executor.RUN_HISTORY.clear()

    monkeypatch.setattr(executor.asyncio, "create_subprocess_exec", fake_create_process)

    result = await executor.run_tool("nmap", arguments="-sV 127.0.0.1", dataset=dataset)
    assert "Exit code" in result
    history = executor.get_run_history()
    assert history and history[-1]["tool"] == "nmap"


@pytest.mark.asyncio
async def test_run_tool_applies_resource_limits(monkeypatch, tmp_path):
    dataset = get_dataset()
    policy_path = tmp_path / "policy.yaml"
    policy_path.write_text(
        """
global:
  resource_limits:
    cpu_time_limit: 2
tools:
  nmap:
    resource_limits:
      memory_limit_mb: 64
""",
        encoding="utf-8",
    )

    class FakeResource:
        RLIMIT_CPU = 0
        RLIMIT_AS = 1

        def __init__(self):
            self.calls = []

        def setrlimit(self, which, limits):
            self.calls.append((which, limits))

    fake_resource = FakeResource()

    async def fake_create_process(*args, preexec_fn=None, **kwargs):
        if preexec_fn:
            preexec_fn()

        async def communicate():
            return b"done", b""

        async def wait():
            return 0

        return SimpleNamespace(
            communicate=communicate,
            wait=wait,
            kill=lambda: None,
            returncode=0,
        )

    monkeypatch.setenv("KALI_POLICY_FILE", str(policy_path))
    policy.reload_policy()
    executor.reset_runtime_limits()

    monkeypatch.setattr(executor, "_resource", fake_resource, raising=False)
    monkeypatch.setattr(
        executor.asyncio,
        "create_subprocess_exec",
        fake_create_process,
    )

    result = await executor.run_tool("nmap", dataset=dataset)
    assert "Exit code" in result
    assert fake_resource.calls
    cpu_calls = [call for call in fake_resource.calls if call[0] == fake_resource.RLIMIT_CPU]
    mem_calls = [call for call in fake_resource.calls if call[0] == fake_resource.RLIMIT_AS]
    assert cpu_calls and mem_calls

    monkeypatch.delenv("KALI_POLICY_FILE", raising=False)
    policy.reload_policy()
    executor.reset_runtime_limits()
