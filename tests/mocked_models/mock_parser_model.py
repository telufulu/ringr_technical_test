"""Simulated parser model for tests.

It replaces the LLM that extracts structured data from the conversation. Like
the real parser, it receives nothing from the agent: it reads the conversation
from its own state. Here that state is a list of pre-defined results, and each
call to ``parse_data`` returns the next one, in turn order. This keeps it in
step with the conversation model, which also advances one answer per turn.

Generated with AI following the project design (see docs/ai_usage.md).
"""

from typing import Any


class MockParserModel:
    """Returns pre-defined parser results, one per turn.

    It does not inherit from the ParserModel protocol: it only needs a
    compatible ``parse_data`` method.
    """

    def __init__(self, results: list[dict[str, Any]]) -> None:
        self.results = [dict(result) for result in results]
        self.calls = 0

    def parse_data(self) -> dict[str, Any]:
        if self.calls >= len(self.results):
            raise RuntimeError("MockParserModel has no more scripted results")
        result = self.results[self.calls]
        self.calls += 1
        # A copy, so the agent cannot change the scripted results.
        return dict(result)
