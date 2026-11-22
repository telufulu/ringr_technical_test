"""Contract for the parser model"""

from typing import Any, Protocol

class   ParserModel(Protocol):
    def parse_data(self) -> dict[str, Any]:
        """ Return the data from the conversation model as JSON """
        ...