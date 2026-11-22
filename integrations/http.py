"""Simulated HTTP integration."""

from typing import Any

class HttpRequest:
    """Simulated HTTP request, built but never sent."""

    def __init__(
        self,
        method: str,
        url: str,
        headers: dict[str, str],
        body: dict[str, Any]
    ) -> None:
        self.method = method
        self.url = url
        self.headers = headers
        self.body = body

class HttpClient:
    """Fake HTTP client that records requests instead of sending them."""
    
    def __init__(self) -> None:
        self.requests: list[HttpRequest] = []

    def last_request(self) -> HttpRequest | None:
        return self.requests[-1] if self.requests else None

    def post(
        self,
        url: str,
        headers: dict[str, str],
        body: dict[str, Any]
    ) -> int:
        """Build a POST request, record it and return the HTTP status code."""
        request = HttpRequest(
            method="POST",
            url=url,
            headers=dict(headers),
            body=dict(body)
        )
        self.requests.append(request)
        return 200