# services/chat_service.py
"""Chat service for handling LLM interactions and response parsing."""

import json
from pathlib import Path
from typing import Any, Optional

from config import PROMPTS_DIR


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
        name = customer["name"] if customer["name"] != "du" else "noch unbekannt"
        profil = customer.get("profil", {})

        # Filter out None values for cleaner display
        profil_filled = {k: v for k, v in profil.items() if v is not None}
        profil_str = json.dumps(profil_filled, ensure_ascii=False) if profil_filled else "keine Daten"

        prompt = self.prompt_template
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

        Args:
            response: Raw LLM response string

        Returns:
            Tuple of (reply_text, profil_dict)
        """
        try:
            # Find JSON in response
            start = response.find("{")
            end = response.rfind("}") + 1

            if start != -1 and end > start:
                json_str = response[start:end]
                data = json.loads(json_str)

                reply = data.get("reply", response)
                profil = data.get("profil", {})

                # Filter out null values
                profil = {k: v for k, v in profil.items() if v is not None}

                return reply, profil

        except json.JSONDecodeError:
            pass

        # Fallback: return raw response if parsing fails
        return response, {}
