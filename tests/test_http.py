"""Tests for the simulated HTTP integration."""

import unittest

from integrations.http import HttpClient


class HttpClientTests(unittest.TestCase):
    """HttpClient · simulated HTTP integration"""

    def test_new_client_has_no_requests(self):
        client = HttpClient()

        self.assertEqual(client.requests, [])
        self.assertIsNone(client.last_request())

    def test_post_returns_200_and_records_the_request(self):
        client = HttpClient()
        headers = {"Authorization": "Bearer token"}
        body = {"request": "help"}

        status = client.post("https://example.test/request", headers, body)
        request = client.last_request()

        self.assertEqual(status, 200)
        self.assertEqual(request.method, "POST")
        self.assertEqual(request.url, "https://example.test/request")
        self.assertEqual(request.headers, headers)
        self.assertEqual(request.body, body)

    def test_recorded_request_does_not_change_if_caller_changes_its_dicts(self):
        client = HttpClient()
        headers = {"Authorization": "Bearer token"}
        body = {"request": "help"}

        client.post("https://example.test/request", headers, body)
        headers["Authorization"] = "changed"
        body["request"] = "changed"

        self.assertEqual(client.last_request().headers, {"Authorization": "Bearer token"})
        self.assertEqual(client.last_request().body, {"request": "help"})

    def test_requests_are_recorded_in_order(self):
        client = HttpClient()

        client.post("https://example.test/1", {}, {})
        client.post("https://example.test/2", {}, {})

        self.assertEqual([request.url for request in client.requests], [
            "https://example.test/1",
            "https://example.test/2",
        ])


if __name__ == "__main__":
    unittest.main()
