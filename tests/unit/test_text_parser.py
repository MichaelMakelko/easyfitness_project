"""Unit tests for text_parser.py - Pure function tests."""

import pytest
from freezegun import freeze_time

from utils.text_parser import (
    extract_booking_intent,
    extract_date_only,
    extract_date_time,
    extract_email,
    extract_name,
    extract_time_only,
)


class TestExtractName:
    """Tests for extract_name function."""

    @pytest.mark.parametrize(
        "text,expected",
        [
            ("Ich heisse Max", "Max"),
            ("ich heisse anna", "Anna"),
            ("Mein Name ist Thomas Mueller", "Thomas"),
            ("mein name ist maria", "Maria"),
            ("Ich bin der Peter", "Peter"),
            ("ich bin die Lisa", "Lisa"),
            ("Ich bin Hans", "Hans"),
        ],
    )
    def test_extract_name_success(self, text: str, expected: str):
        """Test successful name extraction from various German phrases."""
        assert extract_name(text) == expected

    @pytest.mark.parametrize(
        "text",
        [
            "Hallo, wie geht es?",
            "Was kostet das Training?",
            "Termin um 14 Uhr",
            "",
            "ich bin",
            "Ich heisse",
        ],
    )
    def test_extract_name_none(self, text: str):
        """Test that None is returned when no name pattern found."""
        assert extract_name(text) is None

    def test_extract_name_filters_stopwords(self):
        """Test that common stopwords are filtered out."""
        assert extract_name("ich bin der und") is None
        assert extract_name("ich bin die ich") is None

    def test_extract_name_length_limits(self):
        """Test name length validation (2-20 characters)."""
        assert extract_name("ich bin X") is None  # Too short (1 char)
        # Note: Very long names would be truncated by split logic


class TestExtractBookingIntent:
    """Tests for extract_booking_intent function."""

    @pytest.mark.parametrize(
        "text,reply,expected",
        [
            # Positive cases - keyword + date
            ("Probetraining am 20.01.2025", "", True),
            ("Termin am 20.01.", "", True),
            ("Buchen fuer naechsten Montag", "", True),
            # Positive cases - keyword + time
            ("Probetraining um 14:00", "", True),
            ("Termin 10 Uhr", "", True),
            # Keyword in reply
            ("am 20.01.", "Probetraining", True),
            # Negative cases - keyword only, no date/time
            ("Probetraining", "", False),
            ("Termin buchen", "", False),
            # Negative cases - date/time only, no keyword
            ("Am 20.01.2025 um 14:00", "", False),
            # Negative cases - no relevant content
            ("Hallo wie geht es", "", False),
            ("Was kostet das?", "", False),
        ],
    )
    def test_extract_booking_intent(self, text: str, reply: str, expected: bool):
        """Test booking intent detection with various inputs."""
        assert extract_booking_intent(text, reply) == expected

    def test_booking_intent_weekday_keywords(self):
        """Test weekday name detection in German."""
        weekdays = [
            "montag", "dienstag", "mittwoch", "donnerstag",
            "freitag", "samstag", "sonntag"
        ]
        for day in weekdays:
            assert extract_booking_intent(f"Termin am {day}", "") is True

    def test_booking_intent_relative_dates(self):
        """Test relative date expressions in German."""
        # morgen requires umlaut handling
        assert extract_booking_intent("Probetraining morgen", "") is True
        assert extract_booking_intent("Termin diese woche", "") is True

    def test_booking_intent_ausprobieren_keyword(self):
        """Test 'ausprobieren' as booking keyword."""
        assert extract_booking_intent("Kann ich das Training am Montag ausprobieren?", "") is True

    def test_booking_intent_vorbeikommen_keyword(self):
        """Test 'vorbeikommen' as booking keyword."""
        assert extract_booking_intent("Kann ich am 20.01. vorbeikommen?", "") is True


class TestExtractDateOnly:
    """Tests for extract_date_only function."""

    @freeze_time("2025-01-15")
    def test_extract_date_full_format(self):
        """Test DD.MM.YYYY format extraction."""
        assert extract_date_only("am 20.01.2025 um 14 Uhr") == "2025-01-20"
        assert extract_date_only("Termin 5.3.2025") == "2025-03-05"

    @freeze_time("2025-01-15")
    def test_extract_date_short_format(self):
        """Test DD.MM. format (assumes current year)."""
        assert extract_date_only("am 20.01. vorbeikommen") == "2025-01-20"
        assert extract_date_only("5.3.") == "2025-03-05"

    def test_extract_date_none(self):
        """Test that None is returned when no date found."""
        assert extract_date_only("Termin morgen") is None
        assert extract_date_only("Naechsten Montag") is None
        assert extract_date_only("Hallo wie geht es") is None
        assert extract_date_only("") is None

    @freeze_time("2025-01-15")
    def test_extract_date_single_digit_day_month(self):
        """Test single digit day and month are zero-padded."""
        assert extract_date_only("am 5.3.2025") == "2025-03-05"
        assert extract_date_only("am 1.1.") == "2025-01-01"


class TestExtractTimeOnly:
    """Tests for extract_time_only function."""

    @pytest.mark.parametrize(
        "text,expected",
        [
            ("um 14:00 Uhr", "14:00"),
            ("14:30 bitte", "14:30"),
            ("9:00", "09:00"),
            ("10 Uhr", "10:00"),
            ("um 8 uhr morgens", "08:00"),
            ("14 uhr", "14:00"),
        ],
    )
    def test_extract_time_success(self, text: str, expected: str):
        """Test successful time extraction from various formats."""
        assert extract_time_only(text) == expected

    def test_extract_time_none(self):
        """Test that None is returned when no time found."""
        assert extract_time_only("morgen frueh") is None
        assert extract_time_only("am Nachmittag") is None
        assert extract_time_only("") is None

    def test_extract_time_single_digit_hour(self):
        """Test single digit hours are zero-padded."""
        assert extract_time_only("9:30") == "09:30"
        assert extract_time_only("8 uhr") == "08:00"


class TestExtractDateTime:
    """Tests for extract_date_time function."""

    @freeze_time("2025-01-15")
    def test_extract_datetime_both_present(self):
        """Test ISO datetime extraction when both date and time present."""
        result = extract_date_time("Termin am 20.01.2025 um 14:00")
        assert result == "2025-01-20T14:00:00+01:00"

    @freeze_time("2025-01-15")
    def test_extract_datetime_short_date(self):
        """Test with short date format (DD.MM.)."""
        result = extract_date_time("am 20.01. um 10:30")
        assert result == "2025-01-20T10:30:00+01:00"

    def test_extract_datetime_date_only(self):
        """Test that None returned when only date present."""
        assert extract_date_time("am 20.01.2025") is None

    def test_extract_datetime_time_only(self):
        """Test that None returned when only time present."""
        assert extract_date_time("um 14:00 Uhr") is None

    def test_extract_datetime_neither(self):
        """Test that None returned when neither present."""
        assert extract_date_time("morgen frueh") is None
        assert extract_date_time("") is None

    @freeze_time("2025-01-15")
    def test_extract_datetime_x_uhr_format(self):
        """Test with 'X Uhr' time format."""
        result = extract_date_time("Termin am 20.01. um 14 Uhr")
        assert result == "2025-01-20T14:00:00+01:00"


class TestExtractEmail:
    """Tests for extract_email function."""

    @pytest.mark.parametrize(
        "text,expected",
        [
            ("meine email ist max@test.de", "max@test.de"),
            ("Email: anna.schmidt@gmail.com bitte", "anna.schmidt@gmail.com"),
            ("max_mueller123@web.de", "max_mueller123@web.de"),
            ("test.name@subdomain.example.com", "test.name@subdomain.example.com"),
        ],
    )
    def test_extract_email_success(self, text: str, expected: str):
        """Test successful email extraction."""
        assert extract_email(text) == expected

    def test_extract_email_none(self):
        """Test that None returned when no email found."""
        assert extract_email("Hallo wie geht es") is None
        assert extract_email("max at test dot de") is None
        assert extract_email("") is None

    def test_extract_email_lowercase(self):
        """Test that emails are returned in lowercase."""
        assert extract_email("MAX@TEST.DE") == "max@test.de"
        assert extract_email("Anna.Schmidt@Gmail.COM") == "anna.schmidt@gmail.com"

    def test_extract_email_with_numbers(self):
        """Test email extraction with numbers."""
        assert extract_email("test123@mail.de") == "test123@mail.de"

    def test_extract_email_with_dots_and_hyphens(self):
        """Test email extraction with dots and hyphens in local part."""
        assert extract_email("max.mueller-test@mail.de") == "max.mueller-test@mail.de"
