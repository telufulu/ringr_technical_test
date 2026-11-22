"""Tests for AssistanceAgent."""

import io
import unittest
from contextlib import redirect_stdout
from typing import Any

from agents.assistance_agent import AssistanceAgent
from config import API_TOKEN, ASSISTANCE_REQUEST_URL
from integrations.http import HttpClient
from mocked_models.mock_conversation_model import MockConversationModel
from mocked_models.mock_http_client import FailingHttpClient
from mocked_models.mock_parser_model import MockParserModel

CONTRACT_REQUEST = "Necesito una copia de mi contrato"
NORMALIZED_CONTRACT_REQUEST = "necesito una copia de mi contrato"


def make_agent(
    results: list[dict[str, Any]],
    answers: list[str] | None = None,
    http_client: HttpClient | None = None,
) -> AssistanceAgent:
    if answers is None:
        answers = [f"processed answer {turn}" for turn in range(len(results))]
    return AssistanceAgent(MockConversationModel(answers), MockParserModel(results), http_client)


class AssistanceAgentScenarioTests(unittest.TestCase):
    """AssistanceAgent · conversation scenarios"""

    def test_valid_request_is_normalized_and_sent(self):
        agent = make_agent([{"request": CONTRACT_REQUEST}], answers=[CONTRACT_REQUEST])

        self.assertTrue(agent.handle_turn())

        self.assertEqual(len(agent.http_client.requests), 1)
        self.assertEqual(agent.http_client.last_request().body, {"request": NORMALIZED_CONTRACT_REQUEST})
        self.assertEqual(agent.set_keys, {NORMALIZED_CONTRACT_REQUEST})
        self.assertIsNone(agent.temp_request)
        self.assertIsNone(agent.key)

    def test_no_request_does_not_send_anything(self):
        agent = make_agent(
            [{"request": None}],
            answers=["Question about opening hours, no request to register"],
        )

        self.assertTrue(agent.handle_turn())

        self.assertEqual(agent.http_client.requests, [])
        self.assertEqual(agent.set_keys, set())

    def test_duplicate_after_normalization_is_not_sent(self):
        # Same processed text in both turns, different parser output.
        agent = make_agent(
            [{"request": CONTRACT_REQUEST}, {"request": "  NECESITO UNA COPIA DE MI CONTRATO  "}],
            answers=["Asks for a copy of the contract", "Asks for a copy of the contract"],
        )

        agent.handle_turn()
        self.assertTrue(agent.handle_turn())

        self.assertEqual(len(agent.http_client.requests), 1)
        self.assertEqual(agent.set_keys, {NORMALIZED_CONTRACT_REQUEST})
        self.assertIsNone(agent.temp_request)
        self.assertIsNone(agent.key)

    def test_empty_string_and_another_request(self):
        agent = make_agent([{"request": "   "}, {"request": "Una copia de mi contrato"}])

        agent.handle_turn()
        self.assertEqual(agent.http_client.last_request().body, {"request": ""})
        self.assertEqual(agent.set_keys, {""})

        agent.handle_turn()
        self.assertEqual(len(agent.http_client.requests), 2)
        self.assertEqual(agent.set_keys, {"", "una copia de mi contrato"})

    def test_failed_http_response_stops_and_keeps_state(self):
        agent = make_agent([{"request": CONTRACT_REQUEST}], http_client=FailingHttpClient(500))

        with redirect_stdout(io.StringIO()) as output:
            result = agent.handle_turn()

        self.assertFalse(result)
        self.assertIn("Sorry, something went wrong", output.getvalue())
        self.assertEqual(agent.set_keys, set())
        self.assertEqual(agent.temp_request, NORMALIZED_CONTRACT_REQUEST)
        self.assertEqual(agent.key, NORMALIZED_CONTRACT_REQUEST)


class AssistanceAgentRequestTests(unittest.TestCase):
    """AssistanceAgent · simulated HTTP request"""

    def test_request_has_url_auth_and_field_headers(self):
        agent = make_agent([{"request": CONTRACT_REQUEST}])

        agent.handle_turn()
        request = agent.http_client.last_request()

        self.assertEqual(request.method, "POST")
        self.assertEqual(request.url, ASSISTANCE_REQUEST_URL)
        self.assertEqual(request.headers, {
            "Authorization": f"Bearer {API_TOKEN}",
            "Content-Type": "application/json",
            "request": NORMALIZED_CONTRACT_REQUEST,
        })
        self.assertEqual(request.body, {"request": NORMALIZED_CONTRACT_REQUEST})


class AssistanceAgentValidationTests(unittest.TestCase):
    """AssistanceAgent · validation and normalization"""

    def test_normalization_only_applies_lower_and_strip(self):
        agent = make_agent([{"request": "\t Hola, ¿Qué TAL?  \n"}])

        agent.handle_turn()

        self.assertEqual(agent.set_keys, {"hola, ¿qué tal?"})

    def test_text_none_is_a_valid_request(self):
        agent = make_agent([{"request": "None"}])

        agent.handle_turn()

        self.assertEqual(agent.set_keys, {"none"})

    def test_non_string_request_is_discarded(self):
        agent = make_agent([{"request": 5}])

        self.assertTrue(agent.handle_turn())

        self.assertIsNone(agent.temp_request)
        self.assertEqual(agent.http_client.requests, [])

    def test_missing_request_field_is_treated_as_no_request(self):
        agent = make_agent([{}])

        agent.handle_turn()

        self.assertEqual(agent.http_client.requests, [])


if __name__ == "__main__":
    unittest.main()
