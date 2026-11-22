"""Tests for DebtAgent.

Scenario dates use 2090, which is always in the future. Tests about the
"strictly after today" rule build their dates from ``date.today()``, so the
results do not depend on the day the tests run.
"""

import io
import unittest
from contextlib import redirect_stdout
from datetime import date, timedelta
from typing import Any

from agents.debt_agent import DebtAgent
from config import API_TOKEN, DEBT_COMMITMENT_URL
from integrations.http import HttpClient
from mocked_models.mock_conversation_model import MockConversationModel
from mocked_models.mock_http_client import FailingHttpClient
from mocked_models.mock_parser_model import MockParserModel


def days_from_today(days: int) -> str:
    return (date.today() + timedelta(days=days)).isoformat()


def make_agent(
    results: list[dict[str, Any]],
    answers: list[str] | None = None,
    http_client: HttpClient | None = None,
) -> DebtAgent:
    if answers is None:
        answers = [f"processed answer {turn}" for turn in range(len(results))]
    return DebtAgent(MockConversationModel(answers), MockParserModel(results), http_client)


def run_turns(agent: DebtAgent, turns: int) -> list[bool]:
    return [agent.handle_turn() for _ in range(turns)]


EMPTY_TEMP_DATA = {"commitment_date": None, "committed_amount": None}


class DebtAgentScenarioTests(unittest.TestCase):
    """DebtAgent · conversation scenarios"""

    def test_complete_data_in_one_turn(self):
        agent = make_agent(
            [{"commitment_date": "2090-05-20", "committed_amount": 150.0}],
            answers=["Commitment of 150 euros for 20 May 2090"],
        )

        self.assertTrue(agent.handle_turn())

        self.assertEqual(len(agent.http_client.requests), 1)
        self.assertEqual(agent.set_keys, {("2090-05-20", 150.0)})
        self.assertEqual(agent.temp_data, EMPTY_TEMP_DATA)
        self.assertIsNone(agent.key)

    def test_data_received_in_different_turns(self):
        agent = make_agent([
            {"commitment_date": "2090-05-20", "committed_amount": None},
            {"commitment_date": None, "committed_amount": 150.0},
        ])

        agent.handle_turn()
        self.assertEqual(agent.http_client.requests, [])
        self.assertEqual(agent.temp_data["commitment_date"], "2090-05-20")

        agent.handle_turn()
        self.assertEqual(len(agent.http_client.requests), 1)
        self.assertEqual(
            agent.http_client.last_request().body,
            {"commitment_date": "2090-05-20", "committed_amount": 150.0},
        )
        self.assertEqual(agent.set_keys, {("2090-05-20", 150.0)})
        self.assertEqual(agent.temp_data, EMPTY_TEMP_DATA)

    def test_new_invalid_date_replaces_previous_valid_date(self):
        agent = make_agent([
            {"commitment_date": "2090-05-20", "committed_amount": None},
            {"commitment_date": "2090-02-30", "committed_amount": None},
            {"commitment_date": "2090-05-21", "committed_amount": 150.0},
        ])

        agent.handle_turn()
        agent.handle_turn()
        self.assertIsNone(agent.temp_data["commitment_date"])
        self.assertEqual(agent.http_client.requests, [])

        agent.handle_turn()
        self.assertEqual(len(agent.http_client.requests), 1)
        self.assertEqual(agent.set_keys, {("2090-05-21", 150.0)})

    def test_duplicate_and_different_amount_on_same_date(self):
        agent = make_agent([
            {"commitment_date": "2090-05-20", "committed_amount": 150.0},
            {"commitment_date": "2090-05-20", "committed_amount": 150.0},
            {"commitment_date": "2090-05-20", "committed_amount": 200.0},
        ])

        agent.handle_turn()
        agent.handle_turn()
        # Duplicate: no new request, temporary data cleared, set unchanged.
        self.assertEqual(len(agent.http_client.requests), 1)
        self.assertEqual(agent.temp_data, EMPTY_TEMP_DATA)
        self.assertIsNone(agent.key)
        self.assertEqual(agent.set_keys, {("2090-05-20", 150.0)})

        agent.handle_turn()
        self.assertEqual(len(agent.http_client.requests), 2)
        self.assertEqual(
            agent.set_keys,
            {("2090-05-20", 150.0), ("2090-05-20", 200.0)},
        )

    def test_failed_http_response_stops_and_keeps_state(self):
        agent = make_agent(
            [{"commitment_date": "2090-05-20", "committed_amount": 150.0}],
            http_client=FailingHttpClient(500),
        )

        with redirect_stdout(io.StringIO()) as output:
            result = agent.handle_turn()

        self.assertFalse(result)
        self.assertIn("Sorry, something went wrong", output.getvalue())
        self.assertEqual(len(agent.http_client.requests), 1)
        self.assertEqual(agent.set_keys, set())
        self.assertEqual(
            agent.temp_data,
            {"commitment_date": "2090-05-20", "committed_amount": 150.0},
        )
        self.assertEqual(agent.key, ("2090-05-20", 150.0))


class DebtAgentRequestTests(unittest.TestCase):
    """DebtAgent · simulated HTTP request"""

    def test_request_has_url_auth_headers_and_numeric_body(self):
        agent = make_agent([{"commitment_date": "2090-05-20", "committed_amount": 150.5}])

        agent.handle_turn()
        request = agent.http_client.last_request()

        self.assertEqual(request.method, "POST")
        self.assertEqual(request.url, DEBT_COMMITMENT_URL)
        self.assertEqual(request.headers, {
            "Authorization": f"Bearer {API_TOKEN}",
            "Content-Type": "application/json",
            "commitment_date": "2090-05-20",
            "committed_amount": "150.5",
        })
        self.assertEqual(request.body, {"commitment_date": "2090-05-20", "committed_amount": 150.5})
        self.assertIsInstance(request.body["committed_amount"], float)


class DebtAgentValidationTests(unittest.TestCase):
    """DebtAgent · validation and normalization"""

    def test_tomorrow_is_a_valid_date(self):
        tomorrow = days_from_today(1)
        agent = make_agent([{"commitment_date": tomorrow, "committed_amount": 10.0}])

        agent.handle_turn()

        self.assertEqual(agent.set_keys, {(tomorrow, 10.0)})

    def test_invalid_dates_are_rejected(self):
        invalid_dates = {
            "today": days_from_today(0),
            "past date": days_from_today(-1),
            "non-existent date": "2090-02-30",
            "single-digit month": "2090-5-20",
            "compact ISO format": "20900520",
            "day-month-year order": "20-05-2090",
            "not a string": 20900520,
        }
        for label, invalid_date in invalid_dates.items():
            with self.subTest(label):
                agent = make_agent([{"commitment_date": invalid_date, "committed_amount": 150.0}])

                self.assertTrue(agent.handle_turn())

                self.assertIsNone(agent.temp_data["commitment_date"])
                self.assertEqual(agent.temp_data["committed_amount"], 150.0)
                self.assertIsNone(agent.key)
                self.assertEqual(agent.http_client.requests, [])

    def test_invalid_amounts_are_rejected(self):
        invalid_amounts = {
            "zero": 0,
            "negative": -10.0,
            "boolean": True,
            "numeric string": "150",
            "infinity": float("inf"),
            "not a number": float("nan"),
        }
        for label, invalid_amount in invalid_amounts.items():
            with self.subTest(label):
                agent = make_agent([{"commitment_date": "2090-05-20", "committed_amount": invalid_amount}])

                agent.handle_turn()

                self.assertIsNone(agent.temp_data["committed_amount"])
                self.assertEqual(agent.temp_data["commitment_date"], "2090-05-20")
                self.assertEqual(agent.http_client.requests, [])

    def test_integer_amount_is_accepted_as_float_without_rounding(self):
        for amount, expected in ((150, 150.0), (0.01, 0.01), (99.999, 99.999)):
            with self.subTest(amount=amount):
                agent = make_agent([{"commitment_date": "2090-05-20", "committed_amount": amount}])

                agent.handle_turn()
                sent_amount = agent.http_client.last_request().body["committed_amount"]

                self.assertEqual(sent_amount, expected)
                self.assertIsInstance(sent_amount, float)

    def test_new_invalid_amount_replaces_previous_amount_and_keeps_date(self):
        agent = make_agent([
            {"commitment_date": None, "committed_amount": 150.0},
            {"commitment_date": "2090-05-20", "committed_amount": -1},
        ])

        run_turns(agent, 2)

        self.assertEqual(agent.temp_data, {"commitment_date": "2090-05-20", "committed_amount": None})
        self.assertEqual(agent.http_client.requests, [])

    def test_missing_fields_are_treated_as_not_supplied(self):
        agent = make_agent([{"commitment_date": "2090-05-20"}, {}])

        run_turns(agent, 2)

        self.assertEqual(agent.temp_data["commitment_date"], "2090-05-20")
        self.assertEqual(agent.http_client.requests, [])


if __name__ == "__main__":
    unittest.main()
