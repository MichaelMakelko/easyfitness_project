# services/chat_service.py
"""Chat service for handling LLM interactions and response parsing."""

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

from config import PROMPTS_DIR
from constants import BotMessages

# German weekday names
WOCHENTAGE = ["Montag", "Dienstag", "Mittwoch", "Donnerstag", "Freitag", "Samstag", "Sonntag"]


class ChatService:
    """Handles LLM prompt building and response parsing."""

    PROMPT_FILE = PROMPTS_DIR / "fitnesstrainer_prompt.txt"

    def __init__(self, llm_model: Any):
        """
        Initialize chat service.

        Args:
            llm_model: LLM model instance with generate() method
        """
        self.llm = llm_model
        self.prompt_template = self._load_prompt_template()

    def _load_prompt_template(self) -> str:
        """Load system prompt template from file."""
        if self.PROMPT_FILE.exists():
            with open(self.PROMPT_FILE, "r", encoding="utf-8") as f:
                return f.read()
        raise FileNotFoundError(f"Prompt file not found: {self.PROMPT_FILE}")

    def build_system_prompt(self, customer: dict[str, Any]) -> str:
        """
        Build system prompt with customer data.

        Args:
            customer: Customer data dictionary

        Returns:
            Formatted system prompt
        """
        name = customer["name"] if customer["name"] != BotMessages.DEFAULT_NAME else BotMessages.NAME_UNKNOWN
        profil = customer.get("profil", {})

        # Filter out None values for cleaner display
        profil_filled = {k: v for k, v in profil.items() if v is not None}
        profil_str = json.dumps(profil_filled, ensure_ascii=False) if profil_filled else BotMessages.NO_PROFILE_DATA

        # Get current date info
        heute = datetime.now()
        wochentag = WOCHENTAGE[heute.weekday()]
        datum = heute.strftime("%d.%m.%Y")

        prompt = self.prompt_template
        prompt = prompt.replace("{{WOCHENTAG}}", wochentag)
        prompt = prompt.replace("{{DATUM}}", datum)
        prompt = prompt.replace("{{NAME}}", name)
        prompt = prompt.replace("{{STATUS}}", customer["status"])
        prompt = prompt.replace("{{PROFIL}}", profil_str)

        return prompt

    def build_messages(
        self, customer: dict[str, Any], history: list[dict[str, str]]
    ) -> list[dict[str, str]]:
        """
        Build full message list for LLM.

        Args:
            customer: Customer data dictionary
            history: Recent conversation history

        Returns:
            List of message dictionaries for LLM
        """
        system_prompt = self.build_system_prompt(customer)
        messages = [{"role": "system", "content": system_prompt}]
        messages.extend(history)
        return messages

    def generate_response(
        self, customer: dict[str, Any], history: list[dict[str, str]], user_message: str
    ) -> tuple[str, dict[str, Any]]:
        """
        Generate bot response and extract profile data.

        Args:
            customer: Customer data dictionary
            history: Recent conversation history
            user_message: Current user message

        Returns:
            Tuple of (reply_text, extracted_profil_dict)
        """
        messages = self.build_messages(customer, history)
        messages.append({"role": "user", "content": user_message})

        raw_response = self.llm.generate(messages)
        reply, profil = self._parse_response(raw_response)

        return reply, profil

    def _parse_response(self, response: str) -> tuple[str, dict[str, Any]]:
        """
        Parse JSON response from LLM.

        Extracts reply text and profile data from structured response.
        Handles both proper JSON (double quotes) and Python dict syntax (single quotes).

        Args:
            response: Raw LLM response string

        Returns:
            Tuple of (reply_text, profil_dict)
        """
        # Find dict/JSON in response
        start = response.find("{")
        end = response.rfind("}") + 1

        if start == -1 or end <= start:
            # No JSON-like structure found
            print(f"⚠️ No JSON structure in response: {response[:100]}...")
            return response, {}

        json_str = response[start:end]

        # Try 1: Standard JSON parsing
        try:
            data = json.loads(json_str)
            return self._extract_reply_profil(data, response)
        except json.JSONDecodeError:
            pass

        # Try 2: Python dict syntax (single quotes) - convert to JSON
        try:
            # Replace single quotes with double quotes carefully
            # Handle None -> null, True -> true, False -> false
            fixed_str = json_str.replace("'", '"')
            fixed_str = fixed_str.replace("None", "null")
            fixed_str = fixed_str.replace("True", "true")
            fixed_str = fixed_str.replace("False", "false")
            data = json.loads(fixed_str)
            print("⚠️ LLM returned Python dict syntax instead of JSON - converted successfully")
            return self._extract_reply_profil(data, response)
        except json.JSONDecodeError:
            pass

        # Try 3: Use ast.literal_eval for Python literals
        try:
            import ast
            data = ast.literal_eval(json_str)
            if isinstance(data, dict):
                print("⚠️ LLM returned Python dict - parsed with ast.literal_eval")
                return self._extract_reply_profil(data, response)
        except (ValueError, SyntaxError):
            pass

        # All parsing failed - log and return raw
        print(f"❌ Failed to parse LLM response: {json_str[:200]}...")
        return response, {}

    def _extract_reply_profil(self, data: dict, fallback: str) -> tuple[str, dict[str, Any]]:
        """Extract reply and profil from parsed data dict."""
        reply = data.get("reply", fallback)
        profil = data.get("profil", {})

        # Filter out null/None values
        if isinstance(profil, dict):
            profil = {k: v for k, v in profil.items() if v is not None}
        else:
            profil = {}

        return reply, profil
