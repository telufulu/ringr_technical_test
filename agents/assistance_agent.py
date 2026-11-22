from typing import Any

from config import API_TOKEN, ASSISTANCE_REQUEST_URL

from agents.agent import Agent, ActionFailedError

from integrations.http import HttpClient

from models.conversation_model import ConversationModel
from models.parser_model import ParserModel

class AssistanceAgent(Agent):
    def __init__(
        self,
        conversation_model: ConversationModel,
        parser_model: ParserModel,
        http_client: HttpClient | None = None,
    ) -> None:
        super().__init__(conversation_model, parser_model)
        self.http_client = http_client if http_client is not None else HttpClient()
        self.temp_request: str | None = None

    # Abstracts from parent
    def clear_temp_data(self) -> None:
        self.temp_request = None

    def normalize_data(self, parsed_data: dict[str, Any]) -> None:
        raw_request = parsed_data.get("request")
        if isinstance(raw_request, str):    # Empty string is a valid request.
            self.temp_request = raw_request.lower().strip()
        elif raw_request is not None:
            self.temp_request = None    # None means "not supplied this turn": keep the stored value.
        self.key = self.temp_request

    def exec_action(self) -> None:
        request = self.temp_request
        headers = {
            "Authorization": f"Bearer {API_TOKEN}",
            "Content-Type": "application/json",
            "request": request,
        }
        body = {"request": request}
        status = self.http_client.post(ASSISTANCE_REQUEST_URL, headers, body)
        if status != 200:
            raise ActionFailedError(f"Assistance request failed with HTTP {status}")
