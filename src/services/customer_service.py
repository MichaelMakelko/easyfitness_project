# services/customer_service.py
"""Customer database service for managing customer profiles and history."""

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

from config import MEMORY_FILE
from constants import BotMessages, CustomerStatus


class CustomerService:
    """Handles customer data persistence and profile management."""

    def __init__(self, memory_file: Optional[Path] = None):
        self.memory_file = memory_file or MEMORY_FILE
        self.customers: dict[str, dict[str, Any]] = self._load()

    def _load(self) -> dict[str, dict[str, Any]]:
        """Load customers from JSON file."""
        if self.memory_file.exists():
            with open(self.memory_file, "r", encoding="utf-8") as f:
                return json.load(f)
        return {}

    def save(self) -> None:
        """Save customers to JSON file."""
        with open(self.memory_file, "w", encoding="utf-8") as f:
            json.dump(self.customers, f, indent=2, ensure_ascii=False)

    def _default_profil(self) -> dict[str, Any]:
        """Create default customer profile template."""
        return {
            # MagicLine Integration
            "magicline_customer_id": None,  # Set manually after customer registers
            # Personal Data (required for trial offer booking)
            "vorname": None,
            "nachname": None,
            # Booking request data (temporary storage for multi-message booking)
            "datum": None,  # Requested date in YYYY-MM-DD format
            "uhrzeit": None,  # Requested time in HH:MM format
            "alter": None,
            "geschlecht": None,
            "wohnort": None,
            "beruf": None,
            "email": None,
            # Fitness Qualification
            "fitness_ziel": None,
            "fitness_level": None,
            "fitness_erfahrung": None,
            "trainingsfrequenz": None,
            "aktuelles_studio": None,
            "gesundheitliche_einschraenkungen": None,
            # Sales Qualification
            "budget_bewusst": None,
            "zeitfenster": None,
            "entscheidungstraeger": None,
            "dringlichkeit": None,
            "wie_gefunden": None,
            # Lead Scoring
            "interesse_level": None,
            "probetraining_datum": None,
            "follow_up_datum": None,
            # Booking Tracking
            "last_booking_id": None,
        }

    def get(self, phone: str) -> dict[str, Any]:
        """
        Get or create customer by phone number.

        Args:
            phone: Customer phone number

        Returns:
            Customer data dictionary
        """
        if phone not in self.customers:
            self.customers[phone] = {
                "name": BotMessages.DEFAULT_NAME,
                "status": CustomerStatus.NEW_LEAD,
                "profil": self._default_profil(),
                "history": [],
                "letzter_kontakt": datetime.now().strftime("%d.%m.%Y %H:%M"),
            }
            self.save()

        # Ensure existing customers have profil field
        if "profil" not in self.customers[phone]:
            self.customers[phone]["profil"] = self._default_profil()
            self.save()

        return self.customers[phone]

    def update_profil(self, phone: str, profil_data: dict[str, Any]) -> None:
        """
        Update customer profile with extracted information.

        Args:
            phone: Customer phone number
            profil_data: Dictionary of profile fields to update
        """
        customer = self.get(phone)

        for key, value in profil_data.items():
            if value is not None and key in customer["profil"]:
                customer["profil"][key] = value

        # Update name from vorname if provided
        if profil_data.get("vorname"):
            customer["name"] = profil_data["vorname"]
        elif profil_data.get("name"):
            customer["name"] = profil_data["name"]

        if profil_data.get("status"):
            customer["status"] = profil_data["status"]

        self.save()

    def update_status(self, phone: str, status: str) -> None:
        """
        Update customer status.

        Args:
            phone: Customer phone number
            status: New status string
        """
        customer = self.get(phone)
        customer["status"] = status
        self.save()

    def update_history(self, phone: str, user_msg: str, bot_reply: str) -> None:
        """
        Append messages to conversation history.

        Args:
            phone: Customer phone number
            user_msg: User's message
            bot_reply: Bot's response
        """
        customer = self.get(phone)
        customer["history"].append({"role": "user", "content": user_msg})
        customer["history"].append({"role": "assistant", "content": bot_reply})

        # Trim history to prevent unlimited growth
        max_history = 100
        keep_history = 80
        if len(customer["history"]) > max_history:
            customer["history"] = customer["history"][-keep_history:]

        customer["letzter_kontakt"] = datetime.now().strftime("%d.%m.%Y %H:%M")
        self.save()

    def get_history(self, phone: str, limit: int = 12) -> list[dict[str, str]]:
        """
        Get recent conversation history.

        Args:
            phone: Customer phone number
            limit: Maximum number of messages to return

        Returns:
            List of message dictionaries
        """
        customer = self.get(phone)
        return customer["history"][-limit:]
