"""
Typed exceptions for tool operations.
"""
from __future__ import annotations


class ToolError(Exception):
    """Base exception for all tool layer errors."""

    pass


class SearchError(ToolError):
    """Raised when a search operation fails."""

    pass


class ScrapeError(ToolError):
    """Raised when a scrape operation fails."""

    pass


class RateLimitError(ToolError):
    """Raised when rate-limited by an external API."""

    def __init__(self, message: str, retry_after: float | None = None) -> None:
        super().__init__(message)
        self.retry_after = retry_after
