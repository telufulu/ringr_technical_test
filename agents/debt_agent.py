from typing import Any
from datetime import date
from math import isfinite
import re

from config import API_TOKEN, DEBT_COMMITMENT_URL

from agents.agent import Agent, ActionFailedError

from integrations.http import HttpClient

from models.conversation_model import ConversationModel
from models.parser_model import ParserModel

DATE_PATTERN = re.compile(r"\d{4}-\d{2}-\d{2}")

class DebtAgent(Agent):
    def __init__(
        self,
        conversation_model: ConversationModel,
        parser_model: ParserModel,
        http_client: HttpClient | None = None,
    ) -> None:
        super().__init__(conversation_model, parser_model)
        self.http_client = http_client if http_client is not None else HttpClient()
        self.temp_data: dict[str, Any] = {}
        self.clear_temp_data()

    # Class internal use methods
    def _validate_date(self, value: Any) -> str | None:
        """Return the date if it is a real YYYY-MM-DD date strictly after today, else None."""
        if not isinstance(value, str) or DATE_PATTERN.fullmatch(value) is None:
            return None
        try:
            parsed = date.fromisoformat(value)
        except ValueError:
            return None
        if parsed > date.today():
            return value
        return None

    def _validate_amount(self, value: Any) -> float | None:
        """Return the amount as a float if it is a finite number greater than zero, else None."""
        # bool is a subclass of int, but True/False are not amounts.
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            return None
        amount = float(value)
        if not isfinite(amount) or amount <= 0:
            return None
        return amount

    # Abstracts declared by parent
    def clear_temp_data(self) -> None:
        self.temp_data = {
            "commitment_date": None,
            "committed_amount": None
        }

    def normalize_data(self, parsed_data: dict[str, Any]) -> None:
        """ None means "not supplied this turn": keep the stored value.
        Any other value replaces it, or resets it to None if invalid."""

        raw_date = parsed_data.get("commitment_date")

        if raw_date is not None:
            self.temp_data["commitment_date"] = self._validate_date(raw_date)
        raw_amount = parsed_data.get("committed_amount")
        if raw_amount is not None:
            self.temp_data["committed_amount"] = self._validate_amount(raw_amount)

        commitment_date = self.temp_data["commitment_date"]
        committed_amount = self.temp_data["committed_amount"]
        if commitment_date is None or committed_amount is None:
            self.key = None
        else:
            self.key = (commitment_date, committed_amount)

    def exec_action(self) -> None:
        commitment_date = self.temp_data["commitment_date"]
        committed_amount = self.temp_data["committed_amount"]
        headers = {
            "Authorization": f"Bearer {API_TOKEN}",
            "Content-Type": "application/json",
            "commitment_date": commitment_date,
            "committed_amount": str(committed_amount),
        }
        body = {
            "commitment_date": commitment_date,
            "committed_amount": committed_amount,
        }
        status = self.http_client.post(DEBT_COMMITMENT_URL, headers, body)
        if status != 200:
            raise ActionFailedError(f"Commitment registration failed with HTTP {status}")
