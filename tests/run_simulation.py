"""Run the scripted conversation simulation, all of it or a part.

Usage, from any directory:

    python3 tests/run_simulation.py               # every conversation
    python3 tests/run_simulation.py debt          # only DebtAgent conversations
    python3 tests/run_simulation.py assistance 3  # only AssistanceAgent conversation 3

The conversations are described in docs/scripted_conversations.md.
"""

import argparse
import sys

from simulations.scripted_conversation import SCENARIOS, run_scenarios

AGENTS = sorted({scenario["agent"] for scenario in SCENARIOS})


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the scripted conversation simulation.")
    parser.add_argument(
        "agent",
        nargs="?",
        choices=AGENTS,
        help="run only the conversations of this agent",
    )
    parser.add_argument(
        "number",
        nargs="?",
        type=int,
        help="run only this conversation of the agent",
    )
    return parser.parse_args()


def select_scenarios(agent: str | None, number: int | None) -> list[dict]:
    if agent is None:
        return SCENARIOS
    selected = [scenario for scenario in SCENARIOS if scenario["agent"] == agent]
    if number is not None:
        selected = [scenario for scenario in selected if scenario["number"] == number]
    return selected


def main() -> int:
    arguments = parse_arguments()
    scenarios = select_scenarios(arguments.agent, arguments.number)
    if not scenarios:
        available = [scenario["number"] for scenario in SCENARIOS if scenario["agent"] == arguments.agent]
        print(
            f"There is no {arguments.agent} conversation number {arguments.number}. "
            f"Available: {', '.join(map(str, available))}.",
            file=sys.stderr,
        )
        return 2
    run_scenarios(scenarios)
    return 0


if __name__ == "__main__":
    sys.exit(main())
