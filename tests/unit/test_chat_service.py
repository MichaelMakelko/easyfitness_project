"""Unit tests for ChatService with mocked LLM."""

import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch
from freezegun import freeze_time

from services.chat_service import ChatService, WOCHENTAGE


@pytest.fixture
def mock_llm():
    """Create mock LLM for chat service."""
    mock = MagicMock()
    mock.generate.return_value = '{"reply": "Hallo! Wie kann ich dir helfen?", "profil": {"vorname": "Max"}}'
    return mock


@pytest.fixture
def chat_service_with_temp_prompt(mock_llm, temp_prompt_file):
    """Create ChatService with mocked LLM and temp prompt file."""
    with patch.object(ChatService, "PROMPT_FILE", temp_prompt_file):
        service = ChatService(mock_llm)
        return service


class TestChatServiceInit:
    """Tests for ChatService initialization."""

    def test_init_loads_prompt_template(self, mock_llm, temp_prompt_file):
        """Test prompt template is loaded on init."""
        with patch.object(ChatService, "PROMPT_FILE", temp_prompt_file):
            service = ChatService(mock_llm)
            assert service.prompt_template is not None
            assert len(service.prompt_template) > 0

    def test_init_raises_on_missing_prompt_file(self, mock_llm):
        """Test FileNotFoundError raised when prompt file missing."""
        with patch.object(ChatService, "PROMPT_FILE", Path("/nonexistent/path.txt")):
            with pytest.raises(FileNotFoundError):
                ChatService(mock_llm)


class TestBuildSystemPrompt:
    """Tests for build_system_prompt method."""

    @freeze_time("2025-01-15")  # Wednesday
    def test_build_system_prompt_injects_date(self, chat_service_with_temp_prompt, sample_customer_new):
        """Test system prompt includes current date and weekday."""
        prompt = chat_service_with_temp_prompt.build_system_prompt(sample_customer_new)

        assert "Mittwoch" in prompt
        assert "15.01.2025" in prompt

    def test_build_system_prompt_injects_customer_name(self, chat_service_with_temp_prompt, sample_customer_with_name):
        """Test system prompt includes customer name."""
        prompt = chat_service_with_temp_prompt.build_system_prompt(sample_customer_with_name)

        assert "Max" in prompt

    def test_build_system_prompt_handles_unknown_name(self, chat_service_with_temp_prompt, sample_customer_new):
        """Test system prompt handles 'du' name correctly."""
        prompt = chat_service_with_temp_prompt.build_system_prompt(sample_customer_new)

        assert "noch unbekannt" in prompt

    def test_build_system_prompt_includes_status(self, chat_service_with_temp_prompt, sample_customer_with_name):
        """Test system prompt includes customer status."""
        prompt = chat_service_with_temp_prompt.build_system_prompt(sample_customer_with_name)

        assert "Name bekannt" in prompt

    def test_build_system_prompt_includes_profil(self, chat_service_with_temp_prompt, sample_customer_with_name):
        """Test system prompt includes non-null profile data."""
        prompt = chat_service_with_temp_prompt.build_system_prompt(sample_customer_with_name)

        assert "Muskelaufbau" in prompt  # fitness_ziel

    def test_build_system_prompt_empty_profil(self, chat_service_with_temp_prompt, sample_customer_new):
        """Test system prompt with empty profile."""
        prompt = chat_service_with_temp_prompt.build_system_prompt(sample_customer_new)

        # Should show "keine Daten" for empty profil
        assert "keine Daten" in prompt

    @freeze_time("2025-01-20")  # Monday
    def test_build_system_prompt_monday(self, chat_service_with_temp_prompt, sample_customer_new):
        """Test correct weekday for Monday."""
        prompt = chat_service_with_temp_prompt.build_system_prompt(sample_customer_new)
        assert "Montag" in prompt

    @freeze_time("2025-01-25")  # Saturday
    def test_build_system_prompt_saturday(self, chat_service_with_temp_prompt, sample_customer_new):
        """Test correct weekday for Saturday."""
        prompt = chat_service_with_temp_prompt.build_system_prompt(sample_customer_new)
        assert "Samstag" in prompt


class TestBuildMessages:
    """Tests for build_messages method."""

    def test_build_messages_structure(self, chat_service_with_temp_prompt, sample_customer_new):
        """Test messages list structure."""
        history = [
            {"role": "user", "content": "Hallo"},
            {"role": "assistant", "content": "Hey!"},
        ]

        messages = chat_service_with_temp_prompt.build_messages(sample_customer_new, history)

        assert messages[0]["role"] == "system"
        assert messages[1] == {"role": "user", "content": "Hallo"}
        assert messages[2] == {"role": "assistant", "content": "Hey!"}

    def test_build_messages_empty_history(self, chat_service_with_temp_prompt, sample_customer_new):
        """Test messages with empty history."""
        messages = chat_service_with_temp_prompt.build_messages(sample_customer_new, [])

        assert len(messages) == 1
        assert messages[0]["role"] == "system"

    def test_build_messages_preserves_history_order(self, chat_service_with_temp_prompt, sample_customer_new):
        """Test history messages are in correct order."""
        history = [
            {"role": "user", "content": "First"},
            {"role": "assistant", "content": "Second"},
            {"role": "user", "content": "Third"},
            {"role": "assistant", "content": "Fourth"},
        ]

        messages = chat_service_with_temp_prompt.build_messages(sample_customer_new, history)

        assert messages[1]["content"] == "First"
        assert messages[2]["content"] == "Second"
        assert messages[3]["content"] == "Third"
        assert messages[4]["content"] == "Fourth"


class TestGenerateResponse:
    """Tests for generate_response method."""

    def test_generate_response_returns_reply_and_profil(self, chat_service_with_temp_prompt, mock_llm, sample_customer_new):
        """Test response parsing extracts reply and profil."""
        reply, profil = chat_service_with_temp_prompt.generate_response(
            sample_customer_new, [], "Hallo!"
        )

        assert reply == "Hallo! Wie kann ich dir helfen?"
        assert profil == {"vorname": "Max"}

    def test_generate_response_calls_llm_with_messages(self, chat_service_with_temp_prompt, mock_llm, sample_customer_new):
        """Test LLM is called with correct message structure."""
        chat_service_with_temp_prompt.generate_response(sample_customer_new, [], "Hallo!")

        call_args = mock_llm.generate.call_args[0][0]
        assert call_args[-1] == {"role": "user", "content": "Hallo!"}

    def test_generate_response_handles_invalid_json(self, chat_service_with_temp_prompt, mock_llm, sample_customer_new):
        """Test fallback when LLM returns invalid JSON."""
        mock_llm.generate.return_value = "This is just plain text response"

        reply, profil = chat_service_with_temp_prompt.generate_response(
            sample_customer_new, [], "Hallo!"
        )

        assert reply == "This is just plain text response"
        assert profil == {}

    def test_generate_response_filters_null_profil_values(self, chat_service_with_temp_prompt, mock_llm, sample_customer_new):
        """Test null values are filtered from profil."""
        mock_llm.generate.return_value = '{"reply": "Test", "profil": {"vorname": "Max", "nachname": null}}'

        reply, profil = chat_service_with_temp_prompt.generate_response(
            sample_customer_new, [], "Hallo!"
        )

        assert "nachname" not in profil
        assert profil["vorname"] == "Max"

    def test_generate_response_includes_history(self, chat_service_with_temp_prompt, mock_llm, sample_customer_new):
        """Test conversation history is included in LLM call."""
        history = [
            {"role": "user", "content": "Previous message"},
            {"role": "assistant", "content": "Previous reply"},
        ]

        chat_service_with_temp_prompt.generate_response(sample_customer_new, history, "New message")

        call_args = mock_llm.generate.call_args[0][0]
        # System prompt + 2 history + 1 new message = 4
        assert len(call_args) == 4


class TestParseResponse:
    """Tests for _parse_response private method."""

    def test_parse_response_extracts_json(self, chat_service_with_temp_prompt):
        """Test JSON extraction from response."""
        response = '{"reply": "Test reply", "profil": {"vorname": "Anna"}}'

        reply, profil = chat_service_with_temp_prompt._parse_response(response)

        assert reply == "Test reply"
        assert profil == {"vorname": "Anna"}

    def test_parse_response_handles_embedded_json(self, chat_service_with_temp_prompt):
        """Test JSON extraction when embedded in text."""
        response = 'Some text before {"reply": "Test", "profil": {}} some text after'

        reply, profil = chat_service_with_temp_prompt._parse_response(response)

        assert reply == "Test"

    def test_parse_response_fallback_on_error(self, chat_service_with_temp_prompt):
        """Test fallback to raw response on parse error."""
        response = "Not valid JSON at all"

        reply, profil = chat_service_with_temp_prompt._parse_response(response)

        assert reply == "Not valid JSON at all"
        assert profil == {}

    def test_parse_response_missing_reply_field(self, chat_service_with_temp_prompt):
        """Test handling when reply field is missing."""
        response = '{"profil": {"vorname": "Max"}}'

        reply, profil = chat_service_with_temp_prompt._parse_response(response)

        # Should use full response as fallback
        assert reply == response
        assert profil == {"vorname": "Max"}

    def test_parse_response_missing_profil_field(self, chat_service_with_temp_prompt):
        """Test handling when profil field is missing."""
        response = '{"reply": "Hello"}'

        reply, profil = chat_service_with_temp_prompt._parse_response(response)

        assert reply == "Hello"
        assert profil == {}

    def test_parse_response_python_dict_syntax(self, chat_service_with_temp_prompt):
        """Test parsing Python dict syntax with single quotes (LLM sometimes returns this)."""
        response = "{'reply': 'Hi! Was kann ich heute für dich tun?', 'profil': {'vorname': None, 'nachname': None}}"

        reply, profil = chat_service_with_temp_prompt._parse_response(response)

        assert reply == "Hi! Was kann ich heute für dich tun?"
        assert profil == {}  # None values should be filtered out

    def test_parse_response_python_dict_with_values(self, chat_service_with_temp_prompt):
        """Test parsing Python dict with actual values."""
        response = "{'reply': 'Hallo Max!', 'profil': {'vorname': 'Max', 'nachname': 'Mueller'}}"

        reply, profil = chat_service_with_temp_prompt._parse_response(response)

        assert reply == "Hallo Max!"
        assert profil == {"vorname": "Max", "nachname": "Mueller"}

    def test_parse_response_python_dict_with_none_and_values(self, chat_service_with_temp_prompt):
        """Test parsing Python dict with mixed None and actual values."""
        response = "{'reply': 'Test', 'profil': {'vorname': 'Anna', 'email': None, 'datum': '2025-01-20'}}"

        reply, profil = chat_service_with_temp_prompt._parse_response(response)

        assert reply == "Test"
        assert profil == {"vorname": "Anna", "datum": "2025-01-20"}
        assert "email" not in profil  # None values filtered


class TestBuildBookingStatus:
    """Tests for _build_booking_status method."""

    def test_build_booking_status_new_customer(self, chat_service_with_temp_prompt):
        """Test booking status for new customer (all null)."""
        profil = {
            "magicline_customer_id": None,
            "vorname": None,
            "nachname": None,
            "email": None,
            "datum": None,
            "uhrzeit": None,
        }

        status = chat_service_with_temp_prompt._build_booking_status(profil)

        assert status["ist_bestandskunde"] is False
        assert status["vorname"] is None
        assert status["nachname"] is None
        assert status["email"] is None
        assert status["datum"] is None
        assert status["uhrzeit"] is None

    def test_build_booking_status_existing_customer(self, chat_service_with_temp_prompt):
        """Test booking status for existing customer with MagicLine ID."""
        profil = {
            "magicline_customer_id": 12345,
            "vorname": "Max",
            "nachname": "Mustermann",
            "email": "max@test.de",
            "datum": None,
            "uhrzeit": None,
        }

        status = chat_service_with_temp_prompt._build_booking_status(profil)

        assert status["ist_bestandskunde"] is True
        assert status["vorname"] == "Max"
        assert status["nachname"] == "Mustermann"
        assert status["email"] == "max@test.de"

    def test_build_booking_status_partial_data(self, chat_service_with_temp_prompt):
        """Test booking status with partial data (mid-booking-flow)."""
        profil = {
            "magicline_customer_id": None,
            "vorname": "Anna",
            "nachname": None,
            "email": "anna@test.de",
            "datum": "2026-01-15",
            "uhrzeit": None,
        }

        status = chat_service_with_temp_prompt._build_booking_status(profil)

        assert status["ist_bestandskunde"] is False
        assert status["vorname"] == "Anna"
        assert status["nachname"] is None
        assert status["email"] == "anna@test.de"
        assert status["datum"] == "2026-01-15"
        assert status["uhrzeit"] is None

    def test_build_booking_status_complete_data(self, chat_service_with_temp_prompt):
        """Test booking status with all data complete."""
        profil = {
            "magicline_customer_id": None,
            "vorname": "Max",
            "nachname": "Mueller",
            "email": "max@test.de",
            "datum": "2026-01-20",
            "uhrzeit": "14:00",
        }

        status = chat_service_with_temp_prompt._build_booking_status(profil)

        assert status["ist_bestandskunde"] is False
        assert status["vorname"] == "Max"
        assert status["nachname"] == "Mueller"
        assert status["email"] == "max@test.de"
        assert status["datum"] == "2026-01-20"
        assert status["uhrzeit"] == "14:00"

    def test_build_booking_status_empty_profil(self, chat_service_with_temp_prompt):
        """Test booking status with completely empty profil (edge case)."""
        profil = {}

        status = chat_service_with_temp_prompt._build_booking_status(profil)

        assert status["ist_bestandskunde"] is False
        assert status["vorname"] is None
        assert status["nachname"] is None
        assert status["email"] is None
        assert status["datum"] is None
        assert status["uhrzeit"] is None

    def test_build_booking_status_only_includes_booking_fields(self, chat_service_with_temp_prompt):
        """Test that booking status only includes booking-relevant fields."""
        profil = {
            "magicline_customer_id": None,
            "vorname": "Max",
            "nachname": "Mustermann",
            "email": "max@test.de",
            "datum": "2026-01-15",
            "uhrzeit": "10:00",
            "fitness_ziel": "Muskelaufbau",
            "alter": 30,
            "wohnort": "Braunschweig",
        }

        status = chat_service_with_temp_prompt._build_booking_status(profil)

        # Should only have 6 keys (booking-relevant)
        assert len(status) == 6
        assert "fitness_ziel" not in status
        assert "alter" not in status
        assert "wohnort" not in status


class TestWochentage:
    """Tests for WOCHENTAGE constant."""

    def test_wochentage_has_seven_days(self):
        """Test WOCHENTAGE has all 7 days."""
        assert len(WOCHENTAGE) == 7

    def test_wochentage_starts_with_montag(self):
        """Test WOCHENTAGE starts with Monday (Python weekday() convention)."""
        assert WOCHENTAGE[0] == "Montag"

    def test_wochentage_ends_with_sonntag(self):
        """Test WOCHENTAGE ends with Sunday."""
        assert WOCHENTAGE[6] == "Sonntag"
