"""Helpers for loading and querying the Kali tool dataset."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from functools import lru_cache
from importlib import resources
from importlib.resources import abc as resources_abc
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Sequence, Union

from rapidfuzz import fuzz

DEFAULT_DATASET_PATHS: Sequence[Union[Path, resources_abc.Traversable]] = (
    Path(os.environ.get("KALI_TOOL_DATA", "")),
    Path(__file__).resolve().parents[2] / "data" / "kali_tools.json",
    resources.files("kali_mcp_server.assets") / "kali_tools.json",
)


@dataclass(frozen=True)
class Tool:
    name: str
    package: str
    category: str
    summary: str
    binary_path: str
    default_args: str

    @property
    def searchable_blob(self) -> str:
        return " ".join(
            [
                self.name.lower(),
                self.package.lower(),
                self.category.lower(),
                self.summary.lower(),
            ]
        )


class ToolDataset:
    def __init__(self, tools: Iterable[Tool]):
        self._tools: List[Tool] = list(tools)
        self._tools_by_name: Dict[str, Tool] = {tool.name.lower(): tool for tool in self._tools}
        self._categories: Dict[str, List[Tool]] = {}
        for tool in self._tools:
            category_key = tool.category.strip()
            self._categories.setdefault(category_key, []).append(tool)
        self._category_lookup = {
            category.lower(): category for category in self._categories.keys()
        }

    @property
    def categories(self) -> List[str]:
        return sorted(self._categories.keys())

    def iter_tools(self) -> Iterable[Tool]:
        return iter(self._tools)

    def by_category(self, category: str) -> List[Tool]:
        key = self._category_lookup.get(category.lower(), category)
        return list(self._categories.get(key, []))

    def get(self, name: str) -> Optional[Tool]:
        key = name.lower().strip()
        tool = self._tools_by_name.get(key)
        if tool:
            return tool
        alt_key = key.replace(" ", "-")
        return self._tools_by_name.get(alt_key)

    def fuzzy_search(self, query: str, limit: int = 10) -> List[Tool]:
        if not query.strip():
            return []

        limit = max(1, limit)
        scored = []
        query_lc = query.lower()
        for tool in self._tools:
            blob_score = fuzz.token_set_ratio(query, tool.searchable_blob)
            name_score = fuzz.ratio(query_lc, tool.name.lower())
            scored.append((max(blob_score, name_score), tool))
        scored.sort(key=lambda item: item[0], reverse=True)

        filtered = [tool for score, tool in scored if score > 40]
        if not filtered:
            filtered = [tool for score, tool in scored if score > 0]
        if not filtered:
            filtered = [tool for _score, tool in scored]

        return filtered[:limit]


def load_dataset(
    paths: Iterable[Union[Path, resources_abc.Traversable]] = DEFAULT_DATASET_PATHS,
) -> ToolDataset:
    for candidate in paths:
        if not candidate:
            continue
        if isinstance(candidate, Path):
            json_path = candidate
            if candidate.is_dir():
                json_path = candidate / "kali_tools.json"
            if json_path.exists():
                tools = _load_tools_from_json(json_path)
                return ToolDataset(tools)
        else:
            with resources.as_file(candidate) as tmp:
                tools = _load_tools_from_json(tmp)
                return ToolDataset(tools)
    raise FileNotFoundError("No kali tool dataset found; run scripts/sync_tools.py")


@lru_cache(maxsize=1)
def get_dataset() -> ToolDataset:
    return load_dataset()


def _load_tools_from_json(path: Path) -> List[Tool]:
    payload = json.loads(path.read_text())
    tools = []
    for entry in payload:
        tools.append(
            Tool(
                name=entry["name"],
                package=entry["package"],
                category=entry["category"],
                summary=entry["summary"],
                binary_path=entry["binary_path"],
                default_args=entry.get("default_args", ""),
            )
        )
    return tools
