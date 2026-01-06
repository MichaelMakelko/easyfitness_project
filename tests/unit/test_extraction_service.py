"""Unit tests for ExtractionService with mocked LLM."""

import pytest
from datetime import datetime, timedelta
from unittest.mock import MagicMock

from constants import build_datetime_iso
from services.extraction_service import ExtractionService


@pytest.fixture
def mock_llm():
    """Create mock LLM for extraction service."""
    return MagicMock()


@pytest.fixture
def extraction_service(mock_llm):
    """Create ExtractionService with mocked LLM."""
    return ExtractionService(mock_llm)


@pytest.fixture
def future_date():
    """Get a valid future date (tomorrow) for testing."""
    tomorrow = datetime.now() + timedelta(days=1)
    return tomorrow.strftime("%Y-%m-%d")


class TestExtractCustomerData:
    """Tests for extract_customer_data method."""

    def test_extract_full_data(self, extraction_service, mock_llm, future_date):
        """Test extraction of all fields from LLM response."""
        mock_llm.generate_extraction.return_value = f'''
        {{"vorname": "Max", "nachname": "Mustermann", "email": "max@test.de", "datum": "{future_date}", "uhrzeit": "14:00"}}
        '''

        result = extraction_service.extract_customer_data("Test message")

        assert result["vorname"] == "Max"
        assert result["nachname"] == "Mustermann"
        assert result["email"] == "max@test.de"
        assert result["datum"] == future_date
        assert result["uhrzeit"] == "14:00"

    def test_extract_partial_data(self, extraction_service, mock_llm):
        """Test extraction when only some fields present."""
        mock_llm.generate_extraction.return_value = '{"vorname": "Max", "nachname": null, "email": null, "datum": null, "uhrzeit": null}'

        result = extraction_service.extract_customer_data("Ich bin Max")

        assert result["vorname"] == "Max"
        assert result["nachname"] is None
        assert result["email"] is None

    def test_extract_handles_json_in_text(self, extraction_service, mock_llm):
        """Test extraction finds JSON embedded in text."""
        mock_llm.generate_extraction.return_value = '''
        Some preamble text.
        {"vorname": "Anna", "nachname": "Schmidt", "email": "anna@test.de", "datum": null, "uhrzeit": null}
        Some trailing text.
        '''

        result = extraction_service.extract_customer_data("Test")

        assert result["vorname"] == "Anna"
        assert result["nachname"] == "Schmidt"

    def test_extract_handles_invalid_json(self, extraction_service, mock_llm):
        """Test extraction returns empty dict on invalid JSON."""
        mock_llm.generate_extraction.return_value = "This is not valid JSON at all"

        result = extraction_service.extract_customer_data("Test")

        assert result == {
            "vorname": None,
            "nachname": None,
            "email": None,
            "datum": None,
            "uhrzeit": None,
        }

    def test_extract_handles_llm_exception(self, extraction_service, mock_llm):
        """Test extraction handles LLM exceptions gracefully."""
        mock_llm.generate_extraction.side_effect = Exception("LLM Error")

        result = extraction_service.extract_customer_data("Test")

        assert result["vorname"] is None
        assert result["nachname"] is None

    def test_extract_filters_null_string_values(self, extraction_service, mock_llm, future_date):
        """Test that 'null' and 'none' string values are converted to None."""
        mock_llm.generate_extraction.return_value = f'{{"vorname": "null", "nachname": "none", "email": "", "datum": "{future_date}", "uhrzeit": "14:00"}}'

        result = extraction_service.extract_customer_data("Test")

        assert result["vorname"] is None
        assert result["nachname"] is None
        assert result["email"] is None
        assert result["datum"] == future_date

    def test_extract_calls_llm_with_correct_messages(self, extraction_service, mock_llm):
        """Test LLM is called with correct message structure."""
        mock_llm.generate_extraction.return_value = '{"vorname": null, "nachname": null, "email": null, "datum": null, "uhrzeit": null}'

        extraction_service.extract_customer_data("Hallo, ich bin Max!")

        call_args = mock_llm.generate_extraction.call_args[0][0]
        assert call_args[0]["role"] == "system"
        assert call_args[1]["role"] == "user"
        assert "Hallo, ich bin Max!" in call_args[1]["content"]

    def test_extract_trims_whitespace(self, extraction_service, mock_llm):
        """Test extracted values have whitespace trimmed."""
        mock_llm.generate_extraction.return_value = '{"vorname": "  Max  ", "nachname": " Mustermann ", "email": null, "datum": null, "uhrzeit": null}'

        result = extraction_service.extract_customer_data("Test")

        assert result["vorname"] == "Max"
        assert result["nachname"] == "Mustermann"


class TestBuildDatetimeIso:
    """Tests for build_datetime_iso function from constants."""

    def test_build_datetime_iso_success(self):
        """Test ISO datetime string building."""
        result = build_datetime_iso("2025-01-20", "14:00")
        # Timezone will be dynamic (+01:00 or +02:00 depending on DST)
        assert result is not None
        assert result.startswith("2025-01-20T14:00:00")
        assert "+01:00" in result or "+02:00" in result

    def test_build_datetime_iso_missing_date(self):
        """Test returns None when date missing."""
        result = build_datetime_iso(None, "14:00")
        assert result is None

    def test_build_datetime_iso_missing_time(self):
        """Test returns None when time missing."""
        result = build_datetime_iso("2025-01-20", None)
        assert result is None

    def test_build_datetime_iso_both_missing(self):
        """Test returns None when both missing."""
        result = build_datetime_iso(None, None)
        assert result is None

    def test_build_datetime_iso_empty_strings(self):
        """Test empty strings are treated as falsy."""
        result = build_datetime_iso("", "14:00")
        assert result is None

        result = build_datetime_iso("2025-01-20", "")
        assert result is None


class TestParseExtractionResponse:
    """Tests for _parse_extraction_response private method."""

    def test_parse_valid_json(self, extraction_service):
        """Test parsing valid JSON response."""
        response = '{"vorname": "Max", "nachname": "Mustermann", "email": "max@test.de", "datum": "2025-01-20", "uhrzeit": "14:00"}'

        result = extraction_service._parse_extraction_response(response)

        assert result["vorname"] == "Max"
        assert result["nachname"] == "Mustermann"
        assert result["email"] == "max@test.de"

    def test_parse_json_with_surrounding_text(self, extraction_service):
        """Test parsing JSON with surrounding text."""
        response = 'Here is the extraction result: {"vorname": "Anna", "nachname": null, "email": null, "datum": null, "uhrzeit": null} End of response.'

        result = extraction_service._parse_extraction_response(response)

        assert result["vorname"] == "Anna"

    def test_parse_malformed_json(self, extraction_service):
        """Test parsing malformed JSON returns default dict."""
        response = '{"vorname": "Max", "nachname": }'  # Invalid JSON

        result = extraction_service._parse_extraction_response(response)

        assert result == {
            "vorname": None,
            "nachname": None,
            "email": None,
            "datum": None,
            "uhrzeit": None,
        }

    def test_parse_no_json_found(self, extraction_service):
        """Test response with no JSON returns default dict."""
        response = "No JSON here at all"

        result = extraction_service._parse_extraction_response(response)

        assert result["vorname"] is None
