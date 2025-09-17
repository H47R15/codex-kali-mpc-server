"""Utilities for querying the NVD API."""

from __future__ import annotations

import httpx
from datetime import datetime, timezone
from typing import Iterable, List, Optional, Sequence, Tuple

CVE_API_URL = "https://services.nvd.nist.gov/rest/json/cves/2.0"


class NVDClientError(Exception):
    """Base exception for NVD client issues."""


class NVDHTTPError(NVDClientError):
    """Raised when the NVD API returns a non-success status code."""

    def __init__(self, status_code: int, message: str = "") -> None:
        super().__init__(message or f"HTTP {status_code}")
        self.status_code = status_code


class NVDEmptyResponse(NVDClientError):
    """Raised when the NVD API returns an unexpected payload."""


async def fetch_latest_cve_summaries(
    keyword: str,
    *,
    limit: int = 3,
    client: Optional[httpx.AsyncClient] = None,
) -> List[Tuple[str, str, str]]:
    """Return a list of (cve_id, published_date, summary) tuples."""
    if not keyword.strip():
        raise ValueError("keyword must be provided")

    params = {
        "keywordSearch": keyword.strip(),
        "resultsPerPage": limit,
        "startIndex": 0,
    }

    owns_client = client is None
    client = client or httpx.AsyncClient(timeout=10.0)

    try:
        response = await client.get(CVE_API_URL, params=params)
        try:
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:  # pragma: no cover - network dependent
            raise NVDHTTPError(exc.response.status_code, str(exc)) from exc
        payload = response.json()
    except httpx.HTTPStatusError as exc:  # pragma: no cover
        raise NVDHTTPError(exc.response.status_code, str(exc)) from exc
    except httpx.RequestError as exc:  # pragma: no cover - network dependent
        raise NVDClientError(str(exc)) from exc
    finally:
        if owns_client:
            await client.aclose()

    vulnerabilities: Sequence[dict] = payload.get("vulnerabilities", [])
    results: List[Tuple[str, str, str]] = []

    for item in vulnerabilities:
        cve_data = item.get("cve", {})
        cve_id = cve_data.get("id", "Unknown CVE")
        descriptions = cve_data.get("descriptions", [])
        summary = (
            descriptions[0].get("value", "No summary provided")
            if descriptions
            else "No summary provided"
        )
        published = cve_data.get("published", "")
        results.append((cve_id, _format_published_date(published), summary))

    return results


def _format_published_date(value: str) -> str:
    if not value:
        return "unknown"
    try:
        published_dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
        return published_dt.astimezone(timezone.utc).strftime("%Y-%m-%d")
    except ValueError:
        return value[:10]


def format_cve_lines(keyword: str, entries: Iterable[Tuple[str, str, str]]) -> str:
    entries = list(entries)
    if not entries:
        return f"No CVEs found for '{keyword}'."
    lines = [f"Latest CVEs mentioning '{keyword}':"]
    for cve_id, published, summary in entries:
        lines.append(f"- {cve_id} ({published}): {summary}")
    return "\n".join(lines)
