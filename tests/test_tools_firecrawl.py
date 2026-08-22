"""
Unit tests for tools/firecrawl_client.py.
Mocks the HTTP layer to ensure 100% offline execution without real API calls.
"""
from __future__ import annotations

import os
from unittest.mock import MagicMock, patch
import pytest

from tools.errors import RateLimitError, ScrapeError, SearchError
from tools.firecrawl_client import search, scrape


@pytest.fixture(autouse=True)
def mock_env():
    with patch.dict(os.environ, {"FIRECRAWL_API_KEY": "fc-test-key-123"}):
        yield


def test_missing_api_key():
    with patch.dict(os.environ, {"FIRECRAWL_API_KEY": ""}, clear=True):
        with pytest.raises(RuntimeError, match="FIRECRAWL_API_KEY is not set"):
            search("test query")


@patch("tools.firecrawl_client.httpx.Client")
def test_search_happy_path(mock_client_cls):
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "success": True,
        "data": [
            {
                "url": "https://example.com/pricing",
                "title": "Example Pricing",
                "description": "Pricing details for Example software",
            }
        ],
    }
    mock_client = mock_client_cls.return_value.__enter__.return_value
    mock_client.request.return_value = mock_response

    hits = search("example pricing", limit=5)
    assert len(hits) == 1
    assert hits[0].url == "https://example.com/pricing"
    assert hits[0].title == "Example Pricing"
    assert hits[0].description == "Pricing details for Example software"


@patch("tools.firecrawl_client.httpx.Client")
def test_scrape_happy_path(mock_client_cls):
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "success": True,
        "data": {
            "markdown": "# Pricing Page\n\n- Pro plan: $49/mo",
            "metadata": {"title": "Pricing | Example", "sourceURL": "https://example.com/pricing"},
        },
    }
    mock_client = mock_client_cls.return_value.__enter__.return_value
    mock_client.request.return_value = mock_response

    page = scrape("https://example.com/pricing")
    assert page.url == "https://example.com/pricing"
    assert page.title == "Pricing | Example"
    assert "Pro plan: $49/mo" in page.markdown


@patch("tools.firecrawl_client.time.sleep", return_value=None)
@patch("tools.firecrawl_client.httpx.Client")
def test_search_rate_limit_retry_and_giveup(mock_client_cls, mock_sleep):
    mock_response = MagicMock()
    mock_response.status_code = 429
    mock_response.headers = {"Retry-After": "0.1"}

    mock_client = mock_client_cls.return_value.__enter__.return_value
    mock_client.request.return_value = mock_response

    with pytest.raises(RateLimitError) as exc_info:
        search("test query", limit=1)
    assert exc_info.value.retry_after == 0.1
    assert mock_client.request.call_count == 4  # Initial + 3 retries


@patch("tools.firecrawl_client.time.sleep", return_value=None)
@patch("tools.firecrawl_client.httpx.Client")
def test_scrape_server_error_retry_and_giveup(mock_client_cls, mock_sleep):
    mock_response = MagicMock()
    mock_response.status_code = 503
    mock_response.text = "Service Unavailable"

    mock_client = mock_client_cls.return_value.__enter__.return_value
    mock_client.request.return_value = mock_response

    # scrape() must raise ScrapeError, not SearchError — the caller distinguishes
    # "couldn't find sources" from "couldn't read the page it found".
    with pytest.raises(ScrapeError, match="server error \\(503\\)"):
        scrape("https://example.com/fail")
    assert mock_client.request.call_count == 4
