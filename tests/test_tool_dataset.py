import json
from pathlib import Path

DATA_PATH = Path(__file__).resolve().parents[1] / "data" / "kali_tools.json"


def test_dataset_exists_with_expected_structure():
    assert DATA_PATH.exists(), "kali_tools.json should exist"
    data = json.loads(DATA_PATH.read_text())
    assert isinstance(data, list) and data, "Dataset should be a non-empty list"
    sample = data[0]
    required_keys = {"name", "package", "category", "summary", "binary_path", "default_args"}
    assert required_keys.issubset(sample.keys())


def test_categories_are_non_empty():
    data = json.loads(DATA_PATH.read_text())
    categories = {entry["category"] for entry in data}
    assert all(category for category in categories)
