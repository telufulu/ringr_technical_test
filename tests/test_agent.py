"""Tests for the shared turn flow in the abstract Agent.

A minimal child agent without HTTP is used, so these tests check the base
flow on its own and show that it does not depend on HTTP actions.
"""

import io
import unittest
from contextlib import redirect_stdout
from typing import Any

from agents.agent import ActionFailedError, Agent
from mocked_models.mock_conversation_model import MockConversationModel
from mocked_models.mock_parser_model import MockParserModel


class RecordingAgent(Agent):
    """Child agent whose action only records the key it was run with."""

    def __init__(self, conversation_model, parser_model, fail: bool = False) -> None:
        super().__init__(conversation_model, parser_model)
        self.fail = fail
        self.executed_keys: list[Any] = []
        self.temp_value: str | None = None

    def normalize_data(self, parsed_data: dict[str, Any]) -> None:
        value = parsed_data.get("value")
        if value is not None:
            self.temp_value = value
        self.key = self.temp_value

    def exec_action(self) -> None:
        self.executed_keys.append(self.key)
        if self.fail:
            raise ActionFailedError("Simulated failure")

    def clear_temp_data(self) -> None:
        self.temp_value = None


def make_agent(results: list[dict[str, Any]], fail: bool = False) -> RecordingAgent:
    answers = [f"processed answer {turn}" for turn in range(len(results))]
    return RecordingAgent(MockConversationModel(answers), MockParserModel(results), fail=fail)


class AgentTests(unittest.TestCase):
    """Agent · shared turn flow"""

    def test_agent_cannot_be_instantiated(self):
        with self.assertRaises(TypeError):
            Agent(MockConversationModel([]), MockParserModel([]))

    def test_new_agent_starts_without_key_and_with_empty_set(self):
        agent = make_agent([])

        self.assertIsNone(agent.key)
        self.assertEqual(agent.set_keys, set())

    def test_conversation_answer_is_passed_to_parser(self):
        conversation = MockConversationModel(["I will pay tomorrow"])
        parser = MockParserModel([{"value": None}])
        agent = RecordingAgent(conversation, parser)

        agent.handle_turn()

        self.assertEqual(parser.received_texts, ["I will pay tomorrow"])

    def test_incomplete_data_does_not_execute_action(self):
        agent = make_agent([{"value": None}])

        self.assertTrue(agent.handle_turn())
        self.assertEqual(agent.executed_keys, [])
        self.assertEqual(agent.set_keys, set())

    def test_successful_action_registers_key_and_clears_state(self):
        agent = make_agent([{"value": "a"}])

        self.assertTrue(agent.handle_turn())

        self.assertEqual(agent.executed_keys, ["a"])
        self.assertEqual(agent.set_keys, {"a"})
        self.assertIsNone(agent.key)
        self.assertIsNone(agent.temp_value)

    def test_duplicate_is_not_executed_and_clears_state_without_changing_set(self):
        agent = make_agent([{"value": "a"}, {"value": "a"}])
        agent.handle_turn()

        self.assertTrue(agent.handle_turn())

        self.assertEqual(agent.executed_keys, ["a"])
        self.assertEqual(agent.set_keys, {"a"})
        self.assertIsNone(agent.key)
        self.assertIsNone(agent.temp_value)

    def test_empty_string_is_a_valid_key(self):
        agent = make_agent([{"value": ""}])

        agent.handle_turn()

        self.assertEqual(agent.executed_keys, [""])
        self.assertEqual(agent.set_keys, {""})

    def test_failed_action_stops_conversation_and_keeps_state(self):
        agent = make_agent([{"value": "a"}], fail=True)
        output = io.StringIO()

        with redirect_stdout(output):
            result = agent.handle_turn()

        self.assertFalse(result)
        self.assertIn("Sorry, something went wrong. Please try again later", output.getvalue())
        self.assertEqual(agent.set_keys, set())
        self.assertEqual(agent.key, "a")
        self.assertEqual(agent.temp_value, "a")
        # No automatic retry: the action ran only once.
        self.assertEqual(agent.executed_keys, ["a"])

    def test_check_duplicates(self):
        agent = make_agent([])
        agent.set_keys.add("a")

        self.assertTrue(agent.check_duplicates("a"))
        self.assertFalse(agent.check_duplicates("b"))


if __name__ == "__main__":
    unittest.main()
