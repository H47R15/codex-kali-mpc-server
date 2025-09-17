import os
import subprocess
from pathlib import Path

import pytest

SKIP_REASON = "Set KALI_INTEGRATION=1 to enable container integration tests."
pytestmark = pytest.mark.skipif(os.environ.get("KALI_INTEGRATION") != "1", reason=SKIP_REASON)


@pytest.fixture(scope="session")
def built_image() -> str:
    repo_root = Path(__file__).resolve().parents[2]

    try:
        subprocess.run(
            ["docker", "info"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=True,
        )
    except subprocess.CalledProcessError as exc:
        pytest.skip(f"Docker daemon unavailable: {exc}")

    override_image = os.environ.get("KALI_TEST_IMAGE")
    if override_image:
        try:
            subprocess.run(["docker", "pull", override_image], check=True)
        except subprocess.CalledProcessError as exc:
            pytest.skip(f"Unable to pull test image {override_image}: {exc}")
        return override_image

    image_tag = os.environ.get("KALI_TEST_IMAGE_TAG", "kali-mcp-test")
    build_cmd = [
        "docker",
        "build",
        "--pull",
        "-t",
        image_tag,
        ".",
    ]
    try:
        subprocess.run(build_cmd, cwd=repo_root, check=True)
    except subprocess.CalledProcessError as exc:
        pytest.skip(f"Docker build failed: {exc}")
    return image_tag


@pytest.mark.integration
def test_nmap_version_inside_container(built_image: str):
    repo_root = Path(__file__).resolve().parents[2]
    result = subprocess.run(
        ["docker", "run", "--rm", built_image, "nmap", "--version"],
        cwd=repo_root,
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr
    assert "Nmap" in result.stdout


@pytest.mark.integration
def test_run_kali_tool_executes_nmap(built_image: str):
    repo_root = Path(__file__).resolve().parents[2]
    script = (
        "import asyncio\n"
        "from kali_mcp_server.executor import run_tool\n\n"
        "async def main():\n"
        "    result = await run_tool(\"nmap\", arguments=\"-sV 127.0.0.1\", timeout=30)\n"
        "    print(result)\n\n"
        "asyncio.run(main())\n"
    )
    result = subprocess.run(
        ["docker", "run", "--rm", built_image, "python", "-c", script],
        cwd=repo_root,
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr
    assert "Exit code:" in result.stdout
    assert "Command: nmap" in result.stdout
