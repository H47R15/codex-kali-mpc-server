import httpx
import pytest

from kali_mcp_server import nvd


def _mock_client(response_or_exception):
    if isinstance(response_or_exception, Exception):
        def handler(_request):
            raise response_or_exception
    else:
        def handler(_request):
            return response_or_exception

    transport = httpx.MockTransport(handler)
    return httpx.AsyncClient(transport=transport)


@pytest.mark.asyncio
async def test_fetch_latest_cve_summaries_success():
    response = httpx.Response(
        200,
        json={
            "vulnerabilities": [
                {
                    "cve": {
                        "id": "CVE-2024-0001",
                        "published": "2024-01-01T00:00:00+00:00",
                        "descriptions": [{"value": "Example summary"}],
                    }
                }
            ]
        },
        request=httpx.Request("GET", nvd.CVE_API_URL),
    )
    async with _mock_client(response) as client:
        entries = await nvd.fetch_latest_cve_summaries("openssl", client=client)
    assert entries == [("CVE-2024-0001", "2024-01-01", "Example summary")]
    formatted = nvd.format_cve_lines("openssl", entries)
    assert "CVE-2024-0001" in formatted


@pytest.mark.asyncio
async def test_fetch_latest_cve_summaries_handles_http_error():
    response = httpx.Response(
        500,
        json={},
        request=httpx.Request("GET", nvd.CVE_API_URL),
    )
    async with _mock_client(response) as client:
        with pytest.raises(nvd.NVDHTTPError) as excinfo:
            await nvd.fetch_latest_cve_summaries("openssl", client=client)
    assert excinfo.value.status_code == 500


@pytest.mark.asyncio
async def test_fetch_latest_cve_summaries_handles_request_error():
    exc = httpx.ConnectError("boom", request=httpx.Request("GET", nvd.CVE_API_URL))
    async with _mock_client(exc) as client:
        with pytest.raises(nvd.NVDClientError):
            await nvd.fetch_latest_cve_summaries("openssl", client=client)
