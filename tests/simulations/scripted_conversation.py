"""Scripted conversation simulation.

Runs the example conversations from the project design with DebtAgent and
AssistanceAgent and prints each turn: the agent's question, the person's
reply, the processed text, the parser output and what the agent did.

This is a simplification to work without a real LLM: the conversation and the
parser are scripted mocks, and the HTTP client is the simulated one, so no
network calls are made. Each conversation starts with a new agent instance
and an empty set of registered keys.

Usage, from any directory:

    python3 tests/simulations/scripted_conversation.py

The conversations come from the project design. The simulation code was
generated with AI (see docs/ai_usage.md).
"""

import os
import sys
from collections.abc import Callable
from pathlib import Path
from typing import Any

TESTS_DIR = Path(__file__).resolve().parents[1]
ROOT_DIR = TESTS_DIR.parent
sys.path[:0] = [str(ROOT_DIR), str(TESTS_DIR)]

from agents.agent import Agent  # noqa: E402
from agents.assistance_agent import AssistanceAgent  # noqa: E402
from agents.debt_agent import DebtAgent  # noqa: E402
from integrations.http import HttpClient  # noqa: E402
from mocked_models.mock_conversation_model import MockConversationModel  # noqa: E402
from mocked_models.mock_http_client import FailingHttpClient  # noqa: E402
from mocked_models.mock_parser_model import MockParserModel  # noqa: E402

USE_COLOR = sys.stdout.isatty() and "NO_COLOR" not in os.environ

BOLD = "\033[1m"
DIM = "\033[2m"
CYAN = "\033[36m"
MAGENTA = "\033[35m"
YELLOW = "\033[33m"
GREEN = "\033[32m"
RED = "\033[31m"
RESET = "\033[0m"


def paint(text: str, *codes: str) -> str:
    if not USE_COLOR:
        return text
    return "".join(codes) + text + RESET


class ScriptedConversationModel(MockConversationModel):
    """Prints the agent's question and the person's reply, then returns the processed text."""

    def __init__(self, turns: list[dict[str, Any]]) -> None:
        super().__init__([turn["processed"] for turn in turns])
        self.turns = turns

    def answer_user(self) -> str:
        turn = self.turns[self.calls]
        print(f"  {paint('Agent: ', BOLD, CYAN)} {turn['agent']}")
        print(f"  {paint('Person:', BOLD, MAGENTA)} {turn['person']}")
        processed = super().answer_user()
        print(paint(f"  Processed text: {processed!r}", DIM))
        return processed


class PrintingParserModel(MockParserModel):
    """Prints the scripted parser output before returning it."""

    def parse_data(self, conversation_text: str) -> dict[str, Any]:
        parsed_data = super().parse_data(conversation_text)
        print(paint(f"  Parser: {parsed_data}", YELLOW))
        return parsed_data


def run_conversation(scenario: dict[str, Any]) -> None:
    """Run every scripted turn of a scenario with one agent instance."""
    turns = scenario["turns"]
    conversation = ScriptedConversationModel(turns)
    parser = PrintingParserModel([turn["parsed"] for turn in turns])
    agent = scenario["agent_class"](conversation, parser, scenario["http_client"]())
    pending_data: Callable[[Any], Any] = scenario["pending_data"]

    title = scenario["title"]
    print()
    print(paint(f"━━ {title} " + "━" * max(3, 72 - len(title)), BOLD))
    print(paint(f"Expected: {scenario['expected']}", DIM))

    for number, turn in enumerate(turns, start=1):
        print()
        print(paint(f"Turn {number}", BOLD))
        requests_before = len(agent.http_client.requests)

        can_continue = agent.handle_turn()

        new_requests = agent.http_client.requests[requests_before:]
        for request in new_requests:
            print(paint(f"  → {request.method} {request.url}", BOLD, GREEN))
            print(paint(f"    body: {request.body}", GREEN))
        if not new_requests:
            print(paint("  → No request sent", DIM))
        print(f"  Pending data: {pending_data(agent)!r}")
        print(f"  Registered keys: {sorted(agent.set_keys, key=str)}")

        if not can_continue:
            print(paint("  Conversation stopped, no retry.", BOLD, RED))
            break


def debt_scenario(
    number: int, title: str, expected: str, turns: list[dict[str, Any]], http_client=HttpClient
) -> dict[str, Any]:
    return {
        "agent": "debt",
        "number": number,
        "title": f"DebtAgent · {number}. {title}",
        "expected": expected,
        "agent_class": DebtAgent,
        "pending_data": lambda agent: agent.temp_data,
        "http_client": http_client,
        "turns": turns,
    }


def assistance_scenario(
    number: int, title: str, expected: str, turns: list[dict[str, Any]], http_client=HttpClient
) -> dict[str, Any]:
    return {
        "agent": "assistance",
        "number": number,
        "title": f"AssistanceAgent · {number}. {title}",
        "expected": expected,
        "agent_class": AssistanceAgent,
        "pending_data": lambda agent: agent.temp_request,
        "http_client": http_client,
        "turns": turns,
    }


def failing_http_client() -> FailingHttpClient:
    return FailingHttpClient(500)


COMPLETE_COMMITMENT_TURN = {
    "agent": "¿Qué importe y fecha quieres comprometer?",
    "person": "Pagaré 150 euros el 20 de mayo de 2090",
    "processed": "Compromiso de 150 euros para el 20 de mayo de 2090",
    "parsed": {"commitment_date": "2090-05-20", "committed_amount": 150.0},
}

CONTRACT_REQUEST_TURN = {
    "agent": "¿En qué puedo ayudarte?",
    "person": "Necesito una copia de mi contrato",
    "processed": "Necesito una copia de mi contrato",
    "parsed": {"request": "Necesito una copia de mi contrato"},
}

SCENARIOS = [
    debt_scenario(
        1, "Complete data in one turn",
        "one POST; the key is registered and the temporary data is cleared",
        [COMPLETE_COMMITMENT_TURN],
    ),
    debt_scenario(
        2, "Data received in different turns",
        "the date is kept until the amount arrives; then one POST",
        [
            {
                "agent": "¿En qué fecha quieres pagar?",
                "person": "El 20 de mayo de 2090",
                "processed": "Fecha de pago: 20 de mayo de 2090",
                "parsed": {"commitment_date": "2090-05-20", "committed_amount": None},
            },
            {
                "agent": "¿Qué importe quieres pagar?",
                "person": "150 euros",
                "processed": "Importe comprometido: 150 euros",
                "parsed": {"commitment_date": None, "committed_amount": 150.0},
            },
        ],
    ),
    debt_scenario(
        3, "New invalid data replaces the previous value",
        "the non-existent date clears the stored one; one POST with the new date",
        [
            {
                "agent": "¿Qué fecha propones?",
                "person": "El 20 de mayo de 2090",
                "processed": "Fecha de pago: 20 de mayo de 2090",
                "parsed": {"commitment_date": "2090-05-20", "committed_amount": None},
            },
            {
                "agent": "¿Quieres cambiar la fecha?",
                "person": "Sí, al 30 de febrero de 2090",
                "processed": "Nueva fecha de pago: 30 de febrero de 2090",
                "parsed": {"commitment_date": "2090-02-30", "committed_amount": None},
            },
            {
                "agent": "Indica una fecha válida y un importe",
                "person": "El 21 de mayo de 2090 y 150 euros",
                "processed": "Compromiso de 150 euros para el 21 de mayo de 2090",
                "parsed": {"commitment_date": "2090-05-21", "committed_amount": 150.0},
            },
        ],
    ),
    debt_scenario(
        4, "Duplicate and different commitment on the same date",
        "two POST requests in total, not three",
        [
            {
                "agent": "¿Qué importe y fecha quieres comprometer?",
                "person": "150 euros el 20 de mayo de 2090",
                "processed": "Compromiso de 150 euros para el 20 de mayo de 2090",
                "parsed": {"commitment_date": "2090-05-20", "committed_amount": 150.0},
            },
            {
                "agent": "¿Quieres registrar otro compromiso?",
                "person": "Sí, 150 euros el 20 de mayo de 2090",
                "processed": "Compromiso de 150 euros para el 20 de mayo de 2090",
                "parsed": {"commitment_date": "2090-05-20", "committed_amount": 150.0},
            },
            {
                "agent": "¿Quieres registrar otro compromiso?",
                "person": "Sí, 200 euros para esa misma fecha",
                "processed": "Compromiso de 200 euros para el 20 de mayo de 2090",
                "parsed": {"commitment_date": "2090-05-20", "committed_amount": 200.0},
            },
        ],
    ),
    debt_scenario(
        5, "Unsuccessful HTTP response",
        "the simulated endpoint answers 500: error message, nothing registered, data kept, conversation stops",
        [{**COMPLETE_COMMITMENT_TURN, "person": "150 euros el 20 de mayo de 2090"}],
        http_client=failing_http_client,
    ),
    assistance_scenario(
        1, "Valid request",
        "one POST with the normalized request; the key is registered",
        [CONTRACT_REQUEST_TURN],
    ),
    assistance_scenario(
        2, "No request",
        "no POST and the set stays empty",
        [
            {
                "agent": "¿En qué puedo ayudarte?",
                "person": "Solo quería saber el horario",
                "processed": "Consulta sobre el horario, sin solicitud para registrar",
                "parsed": {"request": None},
            },
        ],
    ),
    assistance_scenario(
        3, "Duplicate after normalization",
        "the second request normalizes to the same key: one POST in total",
        [
            {
                "agent": "¿Qué solicitud quieres registrar?",
                "person": "Necesito una copia de mi contrato",
                "processed": "Solicita una copia de su contrato",
                "parsed": {"request": "Necesito una copia de mi contrato"},
            },
            {
                "agent": "¿Quieres registrar otra solicitud?",
                "person": "Sí, necesito una copia de mi contrato",
                "processed": "Solicita una copia de su contrato",
                "parsed": {"request": "  NECESITO UNA COPIA DE MI CONTRATO  "},
            },
        ],
    ),
    assistance_scenario(
        4, "Empty string and another request",
        "the empty string is a valid request; two POST requests in total",
        [
            {
                "agent": "¿Qué solicitud quieres registrar?",
                "person": "(introduce una cadena de espacios)",
                "processed": "   ",
                "parsed": {"request": "   "},
            },
            {
                "agent": "¿Hay algo más que quieras solicitar?",
                "person": "Una copia de mi contrato",
                "processed": "Solicita una copia de su contrato",
                "parsed": {"request": "Una copia de mi contrato"},
            },
        ],
    ),
    assistance_scenario(
        5, "Unsuccessful HTTP response",
        "the simulated endpoint answers 500: error message, request kept, conversation stops",
        [{**CONTRACT_REQUEST_TURN, "agent": "¿Qué solicitud quieres registrar?"}],
        http_client=failing_http_client,
    ),
]


def run_scenarios(scenarios: list[dict[str, Any]]) -> None:
    print(paint("Scripted conversation simulation", BOLD))
    print("Questions, replies and parser outputs are scripted. No LLM or network is used.")
    for scenario in scenarios:
        run_conversation(scenario)


def main() -> None:
    run_scenarios(SCENARIOS)


if __name__ == "__main__":
    main()
