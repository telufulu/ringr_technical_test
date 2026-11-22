"""Contract for the parser model"""

from typing import Any, Protocol

class   ParserModel(Protocol):
    def parse_data(self, conversation_str: str) -> dict[str, Any]:
        """ Return the data from the conversation model as JSON """
        ...