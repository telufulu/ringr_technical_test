"""Simulated HTTP clients for tests that need a failed response."""

from typing import Any

from integrations.http import HttpClient


class FailingHttpClient(HttpClient):
    """Records the request like HttpClient but answers with an error status."""

    def __init__(self, status_code: int = 500) -> None:
        super().__init__()
        self.status_code = status_code

    def post(self, url: str, headers: dict[str, str], body: dict[str, Any]) -> int:
        super().post(url, headers, body)
        return self.status_code
