import pytest

from kali_mcp_server.dataset import get_dataset
from kali_mcp_server.server import _format_tool, _format_tool_list


def test_format_tool_includes_core_fields():
    dataset = get_dataset()
    tool = dataset.get("nmap")
    assert tool is not None
    rendered = _format_tool(tool)
    assert "Tool: nmap" in rendered
    assert "Category:" in rendered
    assert "Binary:" in rendered


def test_format_tool_list_lists_entries():
    dataset = get_dataset()
    tools = dataset.by_category("Information Gathering")
    rendered = _format_tool_list("Tools", tools[:2])
    assert rendered.startswith("Tools")
    assert "nmap" in rendered


@pytest.mark.asyncio
async def test_dataset_unknown_tool_suggestions():
    dataset = get_dataset()
    suggestions = dataset.fuzzy_search("nmapp", limit=3)
    assert any(tool.name == "nmap" for tool in suggestions)
