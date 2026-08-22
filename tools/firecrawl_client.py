"""
Firecrawl client wrapper for search and web scraping.
The only module in the repository that communicates with Firecrawl.
"""
from __future__ import annotations

import os
import time
from typing import Any
import httpx
from pydantic import BaseModel, Field

from tools.errors import RateLimitError, ScrapeError, SearchError, ToolError


class SearchHit(BaseModel):
    url: str
    title: str | None = None
    description: str | None = None
    markdown: str | None = None


class ScrapedPage(BaseModel):
    url: str
    title: str | None = None
    markdown: str


def _get_api_key() -> str:
    api_key = os.getenv("FIRECRAWL_API_KEY")
    if not api_key:
        raise RuntimeError(
            "FIRECRAWL_API_KEY is not set. Copy .env.example to .env and fill it in."
        )
    return api_key


def _request_with_retry(
    method: str, endpoint: str, json_body: dict[str, Any], max_retries: int = 3
) -> dict[str, Any]:
    api_key = _get_api_key()
    url = f"https://api.firecrawl.dev/v1/{endpoint}"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    backoff = 1.0
    last_exception: Exception | None = None

    for attempt in range(max_retries + 1):
        try:
            with httpx.Client(timeout=30.0) as client:
                response = client.request(method, url, json=json_body, headers=headers)

            if response.status_code == 429:
                retry_after_header = response.headers.get("Retry-After")
                retry_after = float(retry_after_header) if retry_after_header else backoff
                if attempt == max_retries:
                    raise RateLimitError(
                        f"Firecrawl rate limited (429) on {endpoint} after {max_retries} retries.",
                        retry_after=retry_after,
                    )
                time.sleep(retry_after)
                backoff *= 2
                continue

            if response.status_code in (500, 502, 503, 504):
                if attempt == max_retries:
                    raise SearchError(
                        f"Firecrawl server error ({response.status_code}) on {endpoint} after {max_retries} retries."
                    )
                time.sleep(backoff)
                backoff *= 2
                continue

            if response.status_code >= 400:
                try:
                    err_data = response.json()
                    err_msg = err_data.get("error", response.text)
                except Exception:
                    err_msg = response.text
                if response.status_code == 401:
                    raise SearchError(f"Firecrawl authentication failed (401): {err_msg}")
                raise SearchError(f"Firecrawl API error ({response.status_code}): {err_msg}")

            data = response.json()
            return data

        except (httpx.TimeoutException, httpx.NetworkError) as e:
            last_exception = e
            if attempt == max_retries:
                raise SearchError(f"Firecrawl network/timeout error on {endpoint}: {e}") from e
            time.sleep(backoff)
            backoff *= 2

    if last_exception:
        raise SearchError(f"Firecrawl request failed after {max_retries} retries: {last_exception}")
    raise SearchError(f"Firecrawl request failed after {max_retries} retries.")


def search(query: str, limit: int = 5) -> list[SearchHit]:
    """
    Search the web using Firecrawl search endpoint.
    Never returns an empty list to signal an error — raises appropriate ToolError on failure.
    """
    if not query.strip():
        return []

    body = {"query": query, "limit": limit}
    try:
        result = _request_with_retry("POST", "search", body)
    except (ToolError, RuntimeError):
        # RuntimeError here means misconfiguration (no API key). Wrapping it as a
        # SearchError would tell the Supervisor "search failed" for every lane when
        # the real problem is a missing key — a very expensive thing to misdiagnose.
        raise
    except Exception as e:
        raise SearchError(f"Failed to execute search for '{query}': {e}") from e

    # Firecrawl v1 response format can be {"success": true, "data": [...]} or {"data": [...]}
    items = result.get("data", [])
    if isinstance(items, dict):
        # sometimes data is wrapped or single dict
        items = [items]

    hits: list[SearchHit] = []
    for item in items:
        if isinstance(item, dict):
            hits.append(
                SearchHit(
                    url=item.get("url", ""),
                    title=item.get("title"),
                    description=item.get("description"),
                    markdown=item.get("markdown"),
                )
            )
    return hits


def scrape(url: str) -> ScrapedPage:
    """
    Scrape a URL using Firecrawl scrape endpoint, returning clean markdown text.
    Raises ScrapeError on failure.
    """
    if not url.strip():
        raise ScrapeError("Cannot scrape empty URL.")

    body = {"url": url, "formats": ["markdown"]}
    try:
        result = _request_with_retry("POST", "scrape", body)
    except RateLimitError:
        raise
    except ToolError as e:
        raise ScrapeError(f"Scrape failed for {url}: {e}") from e
    except Exception as e:
        raise ScrapeError(f"Failed to scrape {url}: {e}") from e

    data = result.get("data", result)
    if isinstance(data, dict):
        markdown = data.get("markdown") or data.get("content") or ""
        metadata = data.get("metadata", {})
        title = metadata.get("title") if isinstance(metadata, dict) else None
        page_url = metadata.get("sourceURL") if isinstance(metadata, dict) else url
    else:
        markdown = str(data)
        title = None
        page_url = url

    if not markdown and not result:
        raise ScrapeError(f"Scrape returned empty content for {url}")

    return ScrapedPage(url=page_url or url, title=title, markdown=markdown)
