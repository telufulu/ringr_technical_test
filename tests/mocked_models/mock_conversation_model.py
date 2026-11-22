"""Simulated conversation model for tests.

It replaces the LLM that talks to the person. Each call to ``answer_user``
returns the next pre-scripted processed answer, in order.

Generated with AI following the project design (see docs/ai_usage.md).
"""


class MockConversationModel:
    """Returns pre-scripted processed answers, one per turn.

    It does not inherit from the ConversationModel protocol: it only needs a
    compatible ``answer_user`` method.
    """

    def __init__(self, answers: list[str]) -> None:
        self.answers = list(answers)
        self.calls = 0

    def answer_user(self) -> str:
        if self.calls >= len(self.answers):
            raise RuntimeError("MockConversationModel has no more scripted answers")
        answer = self.answers[self.calls]
        self.calls += 1
        return answer
