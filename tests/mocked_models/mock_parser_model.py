"""Simulated parser model for tests.

It replaces the LLM that extracts structured data. Each call to ``parse_data``
returns the next pre-defined result, in order, and records the text it
received so tests can check what the agent passed to the parser.

Results follow the order of the turns, not the text, because the same
processed text may produce different parser outputs in different turns.

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
        self.received_texts: list[str] = []

    def parse_data(self, conversation_text: str) -> dict[str, Any]:
        turn = len(self.received_texts)
        if turn >= len(self.results):
            raise RuntimeError("MockParserModel has no more scripted results")
        self.received_texts.append(conversation_text)
        # A copy, so the agent cannot change the scripted results.
        return dict(self.results[turn])
