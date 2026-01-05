"""Unit tests for CustomerService with temporary files."""

import json
import pytest
from pathlib import Path
from freezegun import freeze_time

from services.customer_service import CustomerService


class TestCustomerServiceInit:
    """Tests for CustomerService initialization."""

    def test_init_creates_empty_customers_dict(self, temp_customers_file):
        """Test service initializes with empty dict for new file."""
        service = CustomerService(memory_file=temp_customers_file)
        assert service.customers == {}

    def test_init_loads_existing_data(self, temp_customers_file_with_data):
        """Test service loads existing customer data."""
        service = CustomerService(memory_file=temp_customers_file_with_data)
        assert "491234567890" in service.customers
        assert "491111111111" in service.customers


class TestGetCustomer:
    """Tests for get method."""

    def test_get_creates_new_customer(self, temp_customers_file):
        """Test get creates new customer if not exists."""
        service = CustomerService(memory_file=temp_customers_file)

        customer = service.get("491234567890")

        assert customer["name"] == "du"
        assert customer["status"] == "neuer Interessent"
        assert customer["profil"]["vorname"] is None
        assert customer["history"] == []

    def test_get_returns_existing_customer(self, temp_customers_file_with_data):
        """Test get returns existing customer data."""
        service = CustomerService(memory_file=temp_customers_file_with_data)

        customer = service.get("491111111111")

        assert customer["name"] == "Max"
        assert customer["status"] == "Name bekannt"

    def test_get_saves_new_customer_to_file(self, temp_customers_file):
        """Test new customer is persisted to JSON file."""
        service = CustomerService(memory_file=temp_customers_file)
        service.get("491234567890")

        # Read file directly
        with open(temp_customers_file, "r", encoding="utf-8") as f:
            data = json.load(f)

        assert "491234567890" in data

    def test_get_adds_profil_if_missing(self, temp_customers_file):
        """Test profil field is added if missing from existing customer."""
        # Write customer without profil
        with open(temp_customers_file, "w", encoding="utf-8") as f:
            json.dump({"491234567890": {"name": "Test", "status": "test", "history": []}}, f)

        service = CustomerService(memory_file=temp_customers_file)
        customer = service.get("491234567890")

        assert "profil" in customer

    def test_get_customer_has_all_default_profil_fields(self, temp_customers_file):
        """Test new customer has all expected profile fields."""
        service = CustomerService(memory_file=temp_customers_file)
        customer = service.get("491234567890")

        expected_fields = [
            "magicline_customer_id", "vorname", "nachname", "alter", "geschlecht",
            "wohnort", "beruf", "email", "fitness_ziel", "fitness_level",
            "fitness_erfahrung", "trainingsfrequenz", "aktuelles_studio",
            "gesundheitliche_einschraenkungen", "budget_bewusst", "zeitfenster",
            "entscheidungstraeger", "dringlichkeit", "wie_gefunden",
            "interesse_level", "probetraining_datum", "follow_up_datum",
        ]

        for field in expected_fields:
            assert field in customer["profil"]


class TestUpdateProfil:
    """Tests for update_profil method."""

    def test_update_profil_sets_values(self, temp_customers_file):
        """Test profile fields are updated correctly."""
        service = CustomerService(memory_file=temp_customers_file)
        service.get("491234567890")

        service.update_profil("491234567890", {
            "vorname": "Max",
            "nachname": "Mustermann",
            "email": "max@test.de",
        })

        customer = service.get("491234567890")
        assert customer["profil"]["vorname"] == "Max"
        assert customer["profil"]["nachname"] == "Mustermann"
        assert customer["profil"]["email"] == "max@test.de"

    def test_update_profil_ignores_none_values(self, temp_customers_file):
        """Test None values don't overwrite existing data."""
        service = CustomerService(memory_file=temp_customers_file)
        service.get("491234567890")
        service.update_profil("491234567890", {"vorname": "Max"})

        service.update_profil("491234567890", {"vorname": None, "nachname": "Mustermann"})

        customer = service.get("491234567890")
        assert customer["profil"]["vorname"] == "Max"  # Not overwritten
        assert customer["profil"]["nachname"] == "Mustermann"

    def test_update_profil_updates_name_from_vorname(self, temp_customers_file):
        """Test customer name is updated from vorname."""
        service = CustomerService(memory_file=temp_customers_file)
        service.get("491234567890")

        service.update_profil("491234567890", {"vorname": "Max"})

        customer = service.get("491234567890")
        assert customer["name"] == "Max"

    def test_update_profil_updates_name_from_name_field(self, temp_customers_file):
        """Test customer name is updated from name field."""
        service = CustomerService(memory_file=temp_customers_file)
        service.get("491234567890")

        service.update_profil("491234567890", {"name": "Anna"})

        customer = service.get("491234567890")
        assert customer["name"] == "Anna"

    def test_update_profil_ignores_unknown_fields(self, temp_customers_file):
        """Test unknown profile fields are ignored."""
        service = CustomerService(memory_file=temp_customers_file)
        service.get("491234567890")

        service.update_profil("491234567890", {
            "vorname": "Max",
            "unknown_field": "should be ignored",
        })

        customer = service.get("491234567890")
        assert "unknown_field" not in customer["profil"]

    def test_update_profil_updates_status(self, temp_customers_file):
        """Test status can be updated via profil_data."""
        service = CustomerService(memory_file=temp_customers_file)
        service.get("491234567890")

        service.update_profil("491234567890", {"status": "Name bekannt"})

        customer = service.get("491234567890")
        assert customer["status"] == "Name bekannt"

    def test_update_profil_persists_to_file(self, temp_customers_file):
        """Test profile updates are saved to file."""
        service = CustomerService(memory_file=temp_customers_file)
        service.get("491234567890")
        service.update_profil("491234567890", {"vorname": "Max"})

        # Read file directly
        with open(temp_customers_file, "r", encoding="utf-8") as f:
            data = json.load(f)

        assert data["491234567890"]["profil"]["vorname"] == "Max"


class TestUpdateStatus:
    """Tests for update_status method."""

    def test_update_status(self, temp_customers_file):
        """Test customer status is updated correctly."""
        service = CustomerService(memory_file=temp_customers_file)
        service.get("491234567890")

        service.update_status("491234567890", "Name bekannt")

        customer = service.get("491234567890")
        assert customer["status"] == "Name bekannt"

    def test_update_status_persists_to_file(self, temp_customers_file):
        """Test status update is saved to file."""
        service = CustomerService(memory_file=temp_customers_file)
        service.get("491234567890")
        service.update_status("491234567890", "Probetraining gebucht")

        # Read file directly
        with open(temp_customers_file, "r", encoding="utf-8") as f:
            data = json.load(f)

        assert data["491234567890"]["status"] == "Probetraining gebucht"


class TestUpdateHistory:
    """Tests for update_history method."""

    @freeze_time("2025-01-15 14:30:00")
    def test_update_history_adds_messages(self, temp_customers_file):
        """Test messages are added to history."""
        service = CustomerService(memory_file=temp_customers_file)
        service.get("491234567890")

        service.update_history("491234567890", "Hallo!", "Hey, wie kann ich helfen?")

        customer = service.get("491234567890")
        assert len(customer["history"]) == 2
        assert customer["history"][0] == {"role": "user", "content": "Hallo!"}
        assert customer["history"][1] == {"role": "assistant", "content": "Hey, wie kann ich helfen?"}

    @freeze_time("2025-01-15 14:30:00")
    def test_update_history_updates_letzter_kontakt(self, temp_customers_file):
        """Test letzter_kontakt timestamp is updated."""
        service = CustomerService(memory_file=temp_customers_file)
        service.get("491234567890")

        service.update_history("491234567890", "Test", "Reply")

        customer = service.get("491234567890")
        assert customer["letzter_kontakt"] == "15.01.2025 14:30"

    def test_update_history_trims_at_100_messages(self, temp_customers_file):
        """Test history is trimmed when exceeding 100 messages."""
        service = CustomerService(memory_file=temp_customers_file)
        service.get("491234567890")

        # Add 60 message pairs (120 messages total)
        # Trim happens once when >100: at call 51 (102 msgs → 80)
        # Then calls 52-60 add 18 more messages → 98 total
        for i in range(60):
            service.update_history("491234567890", f"User {i}", f"Bot {i}")

        customer = service.get("491234567890")
        # After trim at 102→80, plus 9 more calls (18 msgs) = 98
        assert len(customer["history"]) == 98

    def test_update_history_keeps_most_recent(self, temp_customers_file):
        """Test trimming keeps most recent messages."""
        service = CustomerService(memory_file=temp_customers_file)
        service.get("491234567890")

        # Add 55 message pairs (110 messages, triggers trim to 80)
        for i in range(55):
            service.update_history("491234567890", f"User {i}", f"Bot {i}")

        customer = service.get("491234567890")
        # Most recent should be Bot 54
        assert customer["history"][-1]["content"] == "Bot 54"


class TestGetHistory:
    """Tests for get_history method."""

    def test_get_history_returns_limited_messages(self, temp_customers_file):
        """Test history retrieval respects limit parameter."""
        service = CustomerService(memory_file=temp_customers_file)
        service.get("491234567890")

        # Add 20 message pairs
        for i in range(20):
            service.update_history("491234567890", f"User {i}", f"Bot {i}")

        history = service.get_history("491234567890", limit=10)
        assert len(history) == 10

    def test_get_history_returns_most_recent(self, temp_customers_file):
        """Test history returns most recent messages."""
        service = CustomerService(memory_file=temp_customers_file)
        service.get("491234567890")

        for i in range(10):
            service.update_history("491234567890", f"User {i}", f"Bot {i}")

        history = service.get_history("491234567890", limit=4)
        # Should contain last 4 messages (User 8, Bot 8, User 9, Bot 9)
        assert history[0]["content"] == "User 8"
        assert history[-1]["content"] == "Bot 9"

    def test_get_history_default_limit(self, temp_customers_file):
        """Test default history limit is 12."""
        service = CustomerService(memory_file=temp_customers_file)
        service.get("491234567890")

        for i in range(20):
            service.update_history("491234567890", f"User {i}", f"Bot {i}")

        history = service.get_history("491234567890")
        assert len(history) == 12

    def test_get_history_empty_when_no_messages(self, temp_customers_file):
        """Test empty list returned for customer with no history."""
        service = CustomerService(memory_file=temp_customers_file)
        service.get("491234567890")

        history = service.get_history("491234567890")
        assert history == []
