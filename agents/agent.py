"""Base agent with the turn flow shared by every agent.

Each turn:

1. Get the person's answer from the conversation model and parse it.
2. Let the child agent normalize and validate the data. When the data is
   complete, the child sets ``self.key``.
3. Skip the action if that key was already registered.
4. Otherwise execute the action. Only on success, register the key.

The flow does not assume that actions are HTTP calls: an action succeeds if
``exec_action`` returns and fails if it raises ``ActionFailedError``.
"""

from abc import ABC, abstractmethod
from collections.abc import Hashable
from typing import Any

from models.conversation_model import ConversationModel
from models.parser_model import ParserModel

from config import RED, RESET, FAILURE_MESSAGE

# Exceptions
class ActionFailedError(Exception):
    """Raised by ``exec_action`` when the external action does not succeed."""

# Class
class Agent(ABC):
    """Base agent is not instanciable, we always use a child agent"""
    
    def __init__(
        self,
        conversation_model: ConversationModel,
        parser_model: ParserModel,
    ) -> None:
        self.conversation_model = conversation_model
        self.parser_model = parser_model
        self.key: Hashable | None = None
        self.set_keys: set[Hashable] = set()

    # Class public methods
    def handle_turn(self) -> bool:
        self.conversation_model.answer_user()
        parsed_data = self.parser_model.parse_data()
        self.normalize_data(parsed_data)    # Implemented by child
        
        if self.key is None:
            return True
        if self.check_duplicates(self.key):
            self._clear_pending()
            return True
        try:
            self.exec_action()
        except ActionFailedError:   # No automatic retry.
            print(f"{RED}{FAILURE_MESSAGE}{RESET}")
            return False
        self.set_keys.add(self.key)
        self._clear_pending()
        return True

    def check_duplicates(self, key: Hashable) -> bool:
        return key in self.set_keys

    # Class internal use methods
    def _clear_pending(self) -> None:
        self.clear_temp_data()
        self.key = None

    # Methods implemented by childs
    @abstractmethod
    def normalize_data(self, parsed_data: dict[str, Any]) -> None:
        """Validate ``parsed_data``, update the temporary state and set ``self.key`` when ready."""

    @abstractmethod
    def exec_action(self) -> None:
        """Execute the action for the current temporary data. Raise ``ActionFailedError`` on failure."""

    @abstractmethod
    def clear_temp_data(self) -> None:
        """Reset the child's temporary data after the action has been handled."""
