from pathlib import Path

from kali_mcp_server.dataset import ToolDataset, get_dataset, load_dataset


def test_load_dataset_from_repo_root():
    repo_root = Path(__file__).resolve().parents[1]
    dataset = load_dataset([repo_root / "data" / "kali_tools.json"])
    tool = dataset.get("nmap")
    assert tool is not None
    assert tool.category


def test_dataset_fuzzy_search_returns_results():
    dataset = get_dataset()
    matches = dataset.fuzzy_search("network scan", limit=3)
    assert matches
    assert any(match.name == "nmap" for match in matches)


def test_tooldataset_categories_sorted():
    dataset = get_dataset()
    categories = dataset.categories
    assert categories == sorted(categories)


def test_by_category_case_insensitive():
    dataset = get_dataset()
    tools = dataset.by_category("information gathering")
    assert tools
    assert any(tool.name == "nmap" for tool in tools)
