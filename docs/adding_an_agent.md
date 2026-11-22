🇪🇸 [Leer en español](adding_an_agent.es.md)

# Adding a new agent

This guide explains which files to change to add a new agent, using a fictitious `CallbackAgent` as an example. It registers the phone number a person wants to be called back on.

The shared turn flow lives in `Agent.handle_turn` (`agents/agent.py`) and does not need to change. A new agent only defines its own data, its validation and its action.

## 1. Add the configuration

If the agent calls a new endpoint, add it to `config.py` next to the existing ones:

```python
CALLBACK_REQUEST_URL = "https://api.ringr.callback/v1/request"
```

## 2. Create the agent

Create `agents/callback_agent.py` with a class that inherits from `Agent` and implements its three abstract methods:

| Method | What it must do |
| --- | --- |
| `normalize_data(parsed_data)` | Validate and normalize the parser output, update the temporary data and set `self.key` when the action is ready. Leave `self.key` as `None` while data is missing |
| `exec_action()` | Run the action with the temporary data. Raise `ActionFailedError` if it fails |
| `clear_temp_data()` | Reset the temporary data. The base class calls it after a successful action or a duplicate |

```python
from typing import Any

from agents.agent import ActionFailedError, Agent
from config import API_TOKEN, CALLBACK_REQUEST_URL
from integrations.http import HttpClient
from models.conversation_model import ConversationModel
from models.parser_model import ParserModel


class CallbackAgent(Agent):
    """Registers the phone number a person wants to be called back on."""

    def __init__(
        self,
        conversation_model: ConversationModel,
        parser_model: ParserModel,
        http_client: HttpClient | None = None,
    ) -> None:
        super().__init__(conversation_model, parser_model)
        self.http_client = http_client if http_client is not None else HttpClient()
        self.temp_phone: str | None = None

    def clear_temp_data(self) -> None:
        self.temp_phone = None

    def normalize_data(self, parsed_data: dict[str, Any]) -> None:
        raw_phone = parsed_data.get("callback_phone")
        if isinstance(raw_phone, str) and raw_phone.strip():
            self.temp_phone = raw_phone.strip()
        elif raw_phone is not None:
            self.temp_phone = None
        self.key = self.temp_phone

    def exec_action(self) -> None:
        headers = {
            "Authorization": f"Bearer {API_TOKEN}",
            "Content-Type": "application/json",
            "callback_phone": self.temp_phone,
        }
        body = {"callback_phone": self.temp_phone}
        status = self.http_client.post(CALLBACK_REQUEST_URL, headers, body)
        if status != 200:
            raise ActionFailedError(f"Callback request failed with HTTP {status}")
```

Things to keep in mind:

- **Call `super().__init__`** so the base class creates the models, `key` and the set of registered keys
- **The key must be hashable** (a `str`, a `tuple`...), because it is stored in a `set`. It decides what counts as a duplicate
- **Check for a missing key with `is None`**, not with truthiness, so valid values such as an empty string are not lost
- **`None` from the parser means "not supplied in this turn"**. Keep the stored value in that case, as the existing agents do
- **The action does not have to be HTTP.** The base class only needs `exec_action` to return on success and raise `ActionFailedError` on failure. An agent that does not use HTTP does not need an `http_client`
- **Build the `Authorization` header explicitly** with the token from `config.py`, and add only the known data fields as extra headers, so parser data cannot overwrite it
- **Receive the HTTP client as an optional parameter**, so tests can pass a client that fails

## 3. Add tests

Create `tests/test_callback_agent.py`. Use the mocks in `tests/mocked_models/` to script the conversation and the parser, and `FailingHttpClient` to test the failure branch:

```python
import unittest

from agents.callback_agent import CallbackAgent
from mocked_models.mock_conversation_model import MockConversationModel
from mocked_models.mock_parser_model import MockParserModel


class CallbackAgentScenarioTests(unittest.TestCase):
    """CallbackAgent · conversation scenarios"""

    def test_phone_is_sent_once(self):
        agent = CallbackAgent(
            MockConversationModel(["Call me on 600 000 000", "Call me on 600 000 000"]),
            MockParserModel([{"callback_phone": "600 000 000"}, {"callback_phone": "600 000 000"}]),
        )

        agent.handle_turn()
        agent.handle_turn()

        self.assertEqual(len(agent.http_client.requests), 1)
```

The first line of each `TestCase` docstring, written as `"Component · topic"`, is what `tests/run_tests.py` uses to group the output. New test files named `test_*.py` are found automatically.

## 4. Add simulated conversations (optional)

To show the agent in the scripted simulation, edit `tests/simulations/scripted_conversation.py`:

1. Add a helper like `debt_scenario` or `assistance_scenario` that sets `"agent"` (for example `"callback"`), the agent class and the temporary data to display
2. Add the conversations to `SCENARIOS`

`tests/run_simulation.py` reads the agent names from `SCENARIOS`, so `python3 tests/run_simulation.py callback` works without changing the runner. Describe the new conversations in `docs/scripted_conversations.md` and its Spanish version.

## Summary

| File | Change |
| --- | --- |
| `config.py` | New endpoint, if the agent calls one |
| `agents/<name>_agent.py` | New class that inherits from `Agent` |
| `tests/test_<name>_agent.py` | Tests for the new agent |
| `tests/simulations/scripted_conversation.py` | Optional: conversations for the simulation |
| `docs/scripted_conversations.md` and `.es.md` | Optional: description of those conversations |

No other agent, nor `agents/agent.py`, needs to change.
