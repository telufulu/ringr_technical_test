<div align="center">

[🇬🇧 English](README.md) · [🇪🇸 Español](README.es.md)

</div>

# Ringr Technical Test · Conversational Agents

## Table of Contents

- [Description](#description)
- [Installation](#installation)
  - [Requirements](#requirements)
  - [Setup](#setup)
- [Usage](#usage)
  - [Running the tests](#running-the-tests)
  - [Running the scripted simulation](#running-the-scripted-simulation)
  - [How tests and simulations are organized](#how-tests-and-simulations-are-organized)
  - [Using an agent from code](#using-an-agent-from-code)
- [Features](#features)
- [Design Decisions](#design-decisions)
- [Project Structure](#project-structure)
- [Documentation](#documentation)
- [Known Limitations](#known-limitations)
- [Development Process](#development-process)
- [Resources](#resources)
- [AI Usage Disclosure](#ai-usage-disclosure)
- [Credits](#credits)

## Description

Solution to the Ringr Delivery Engineer technical test: a small object-oriented Python project with two conversational agents that process information from a conversation and run actions through a simulated HTTP integration.

In each turn, an agent gets the person's answer from a conversation model, extracts structured data with a parser model, validates and normalizes it, and decides whether to run an external action:

- **`DebtAgent`** registers payment commitments. When it has a valid date and amount, it sends a POST to `https://api.ringr.debt/v1/commitment`.
- **`AssistanceAgent`** registers customer requests for human agents. When there is a request, it sends a POST to `https://api.ringr.assistance/v1/request`.

No real HTTP or language model calls are made. The goal is a design that is easy to extend to new agents, actions and integrations, while staying clean, robust and testable.

## Installation

### Requirements

- Python 3.10 or later. Tested with Python 3.13 on macOS. Python 3.9 does not work, because the code uses `X | None` type annotations
- No external dependencies: the project only uses the Python standard library

Check your Python version:

    python3 --version

### Setup

    git clone https://github.com/telufulu/ringr_technical_test.git
    cd ringr_technical_test

There is nothing to compile or install.

## Usage

The project has no main program: the agents are meant to receive real conversation and parser models. To see them working, run the tests or the scripted simulation. No Makefile is needed: each one is a single command.

### Running the tests

    python3 tests/run_tests.py

The output is grouped by component (`Agent`, `AssistanceAgent`, `DebtAgent`, `HttpClient`), with one line per test. The last line should be:

    ✓ 35 tests, 0 failures, 0 errors

The script returns exit code 1 if any test fails. The tests can also be run with the standard `unittest` output from the repository root:

    python3 -m unittest discover -s tests -v

### Running the scripted simulation

    python3 tests/run_simulation.py               # all ten conversations
    python3 tests/run_simulation.py debt          # only the DebtAgent ones
    python3 tests/run_simulation.py assistance 3  # only AssistanceAgent conversation 3

Each turn shows the agent's question, the person's reply, the processed text, the parser output and what the agent did. For example, in the first `DebtAgent` conversation the person gives the date and the amount in a single turn, so the agent registers the commitment straight away:

    Turn 1
      Agent:  ¿Qué importe y fecha quieres comprometer?
      Person: Pagaré 150 euros el 20 de mayo de 2090
      Processed text: 'Compromiso de 150 euros para el 20 de mayo de 2090'
      Parser: {'commitment_date': '2090-05-20', 'committed_amount': 150.0}
      → POST https://api.ringr.debt/v1/commitment
        body: {'commitment_date': '2090-05-20', 'committed_amount': 150.0}
      Pending data: {'commitment_date': None, 'committed_amount': None}
      Registered keys: [('2090-05-20', 150.0)]

The conversations are in Spanish, as in the project design. Each one, and what it shows, is described in [docs/scripted_conversations.md](docs/scripted_conversations.md).

Both scripts work from any directory. Colors are turned off when the output is not a terminal or when the `NO_COLOR` environment variable is set.

### How tests and simulations are organized

| Path | Contents |
| --- | --- |
| `tests/test_agent.py` | Shared turn flow, tested with a minimal agent that does not use HTTP |
| `tests/test_debt_agent.py` | `DebtAgent`: conversation scenarios, HTTP request and validation |
| `tests/test_assistance_agent.py` | `AssistanceAgent`: conversation scenarios, HTTP request and validation |
| `tests/test_http.py` | Simulated HTTP client |
| `tests/mocked_models/` | Scripted conversation and parser models, and an HTTP client that answers `500` |
| `tests/simulations/scripted_conversation.py` | The ten scripted conversations |
| `tests/run_tests.py` | Runs every test with grouped, colored output |
| `tests/run_simulation.py` | Runs the whole simulation, one agent or a single conversation |

The tests check the results automatically. The simulation only shows what happens in each turn.

### Using an agent from code

An agent accepts any objects with `answer_user()` and `parse_data()` methods. They do not need to inherit from any class:

```python
from agents.debt_agent import DebtAgent


class MyConversationModel:
    def answer_user(self) -> str:
        return "Commitment of 150 euros for 20 May 2090"


class MyParserModel:
    def parse_data(self) -> dict:
        return {"commitment_date": "2090-05-20", "committed_amount": 150.0}


agent = DebtAgent(MyConversationModel(), MyParserModel())
can_continue = agent.handle_turn()       # True
agent.http_client.last_request().body    # {'commitment_date': '2090-05-20', 'committed_amount': 150.0}
```

Run it from the repository root, so the `agents`, `models`, `integrations` and `config` modules can be imported.

## Features

- Abstract `Agent` class with the shared turn flow in `handle_turn`: get the answer, parse it, normalize it, check for duplicates and run the action
- `DebtAgent`, which collects the date and amount over one or several turns and registers the commitment once both are valid
- `AssistanceAgent`, which normalizes requests with `lower()` and `strip()` and registers them
- Simulated HTTP client that builds the request (method, URL, headers and body), records it so it can be inspected, and returns `200`
- Bearer token authentication, plus one extra header for each parsed field, with the same field names
- No duplicate actions within a conversation
- Failure handling: on a non-`200` response, the agent prints an error, keeps its data and stops the conversation without retrying
- 35 unit tests and ten scripted conversations

## Design Decisions

- **Template method.** `Agent.handle_turn` defines the flow once. Each agent only implements `normalize_data`, `exec_action` and `clear_temp_data`, so a new agent does not change the existing ones.
- **The shared flow does not assume HTTP.** An action succeeds if `exec_action` returns and fails if it raises `ActionFailedError`. Only the agents that need HTTP receive an HTTP client.
- **Model contracts as `Protocol`.** `ConversationModel` and `ParserModel` describe the methods the agents need. Any object with those methods works, without inheritance. The brief says no subclasses of these models are needed.
- **The agent coordinates the models but passes nothing between them.** The conversation model talks to the person and returns a processed, concise version of their answer. The parser reads the conversation from its own state: the brief says both models hold all the information they need, and `parse_data` takes no arguments. The agent only uses the parser output. For this reason `handle_turn` only returns whether the conversation can continue.
- **Data across turns.** `None` from the parser means "not supplied in this turn", so the stored value is kept. A new invalid value clears the stored one.
- **Duplicates.** Each agent keeps a `set` of the keys of the actions already registered: `(date, amount)` for debts and the normalized request for assistance. A key is added only after a `200` response.
- **Extra business rules.** The amount must be greater than zero and the date must be a real `yyyy-mm-dd` date strictly after today. The brief does not require them: they are assumptions of this solution.
- **Configuration.** The token and endpoints are constants in `config.py`. The token is the test value from the brief.

## Project Structure

    ringr_technical_test/
    ├── agents/
    │   ├── agent.py                  # Abstract Agent with the shared turn flow
    │   ├── assistance_agent.py       # AssistanceAgent
    │   └── debt_agent.py             # DebtAgent
    ├── docs/
    │   ├── adding_an_agent.md        # Guide to add a new agent (+ .es.md)
    │   ├── ai_usage.md               # How AI was used in the project (+ .es.md)
    │   └── scripted_conversations.md # The ten scripted conversations (+ .es.md)
    ├── integrations/
    │   └── http.py                   # Simulated HTTP client
    ├── models/
    │   ├── conversation_model.py     # ConversationModel protocol
    │   └── parser_model.py           # ParserModel protocol
    ├── tests/
    │   ├── mocked_models/            # Scripted models and failing HTTP client
    │   ├── simulations/
    │   │   └── scripted_conversation.py
    │   ├── run_simulation.py
    │   ├── run_tests.py
    │   ├── test_agent.py
    │   ├── test_assistance_agent.py
    │   ├── test_debt_agent.py
    │   └── test_http.py
    ├── config.py                     # Token and endpoints
    ├── README.md
    └── README.es.md

## Documentation

- [Adding a new agent](docs/adding_an_agent.md): which files to change and what to keep in mind, with a complete example
- [Scripted conversations](docs/scripted_conversations.md): each conversation in the simulation and what it shows
- [AI usage](docs/ai_usage.md): how AI was used in each area of the project and who made each decision

Every document is available in English and Spanish.

## Known Limitations

- The conversation and parser models are not implemented: they are contracts, and the tests and the simulation use scripted mocks
- There is no interactive chat simulation, only the scripted one
- The set of registered keys lives in memory, per agent instance. It is lost when the process ends and is not shared between conversations
- A commitment is identified by its date and amount, so two real commitments with the same date and amount are treated as one
- If a person corrects the amount after a commitment is registered, a second commitment is registered: the first one is not cancelled
- "Today" is the local date of the machine running the code
- Amounts are `float`, with no upper limit and no rounding, so they are subject to floating-point precision
- Header values are not encoded or checked: the parser is assumed to return text that is valid in an HTTP header
- There is no automatic retry or detailed error handling: a failed action stops the conversation
- The token is stored in `config.py`. In a real system it would be kept out of the code, for example in environment variables

## Development Process

Besides the final solution in `main`, the repository keeps the branches used during development, so the learning and development process can also be reviewed. They show the alternatives that were tried and how the technical decisions evolved during the project.

The exploration branch is [`draft`](https://github.com/telufulu/ringr_technical_test/tree/draft).

## Resources

### Python Documentation

- `abc`: Abstract Base Classes — https://docs.python.org/3/library/abc.html
- `typing.Protocol` — https://docs.python.org/3/library/typing.html#typing.Protocol
- `unittest`: Unit testing framework — https://docs.python.org/3/library/unittest.html
- `argparse`: Command-line parsing — https://docs.python.org/3/library/argparse.html
- `datetime.date.fromisoformat` — https://docs.python.org/3/library/datetime.html#datetime.date.fromisoformat
- `re`: Regular expressions — https://docs.python.org/3/library/re.html
- PEP 8: Style Guide for Python Code — https://peps.python.org/pep-0008/

### README Guidelines

- How to Write a Good README – freeCodeCamp — https://www.freecodecamp.org/news/how-to-write-a-good-readme-file/
- Make a README — https://www.makeareadme.com/

## AI Usage Disclosure

AI assistants (including Claude Code and Notion AI) were used during the project:

- The architecture and design decisions are the author's. They were defined and documented before and during the implementation, and AI was always guided by them
- The base implementation (`agents/`, `models/`, `integrations/` and `config.py`) was written by the author, with AI help for explaining concepts, reference implementations and code review
- The tests, the test mocks, the scripted simulation, the test and simulation runners, and the documentation in `docs/` were generated with AI. The author defined the test cases and conversations in the design; AI wrote the code for them, always supervised and guided by the project's architecture decisions, and the result was reviewed by the author

How AI was used in each area, with examples, is described in [docs/ai_usage.md](docs/ai_usage.md).

## Credits

- telufulu's socials
  - [GitHub](https://github.com/telufulu)
  - [LinkedIn](https://www.linkedin.com/in/teresa-b-lufuluabo-pastor-659702204/)
