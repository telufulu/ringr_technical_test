"""Contract for the conversation model"""

from typing import Protocol

class   ConversationModel(Protocol):
    def answer_user(self) -> str:
        """ Returns a simplified version of the user's answer """
        ...