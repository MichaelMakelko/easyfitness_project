"""Unit tests for text_parser.py - Pure function tests."""

import pytest
from freezegun import freeze_time

from utils.text_parser import (
    extract_booking_intent,
    extract_date_only,
    extract_date_time,
    extract_email,
    extract_full_name,
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
        # Note: "morgen" and "übermorgen" are now recognized!
        assert extract_date_only("Naechsten Montag") is None
        assert extract_date_only("Hallo wie geht es") is None
        assert extract_date_only("") is None

    @freeze_time("2026-01-06")
    def test_extract_date_morgen(self):
        """Test 'morgen' is recognized and returns tomorrow's date."""
        assert extract_date_only("Termin morgen") == "2026-01-07"
        assert extract_date_only("Morgen um 10 Uhr") == "2026-01-07"
        assert extract_date_only("morgen passt gut") == "2026-01-07"
        # "übermorgen" should NOT match as "morgen"
        assert extract_date_only("übermorgen") == "2026-01-08"

    @freeze_time("2026-01-06")
    def test_extract_date_uebermorgen(self):
        """Test 'übermorgen' is recognized and returns day after tomorrow."""
        assert extract_date_only("Termin übermorgen") == "2026-01-08"
        assert extract_date_only("übermorgen um 14 Uhr") == "2026-01-08"

    @freeze_time("2025-01-15")
    def test_extract_date_single_digit_day_month(self):
        """Test single digit day and month are zero-padded."""
        assert extract_date_only("am 5.3.2025") == "2025-03-05"
        # Note: "1.1." is > 7 days in past from Jan 15, so smart year logic picks next year
        assert extract_date_only("am 1.1.") == "2026-01-01"
        # Future date within current year
        assert extract_date_only("am 1.2.") == "2025-02-01"

    @freeze_time("2026-01-06")
    def test_extract_date_short_format_without_trailing_dot(self):
        """Test DD.MM format without trailing dot (common German shorthand)."""
        # "am 9.1" = January 9th
        assert extract_date_only("am 9.1 kommen") == "2026-01-09"
        assert extract_date_only("Ich würde gerne am 9.1 kommen um 10 Uhr") == "2026-01-09"
        assert extract_date_only("den 15.3 um 14 Uhr") == "2026-03-15"
        # With "um" context after date
        assert extract_date_only("9.1 um 10 Uhr") == "2026-01-09"
        # Without context - should NOT match (could be decimal)
        assert extract_date_only("Das kostet 9.1 Euro") is None

    @freeze_time("2026-01-06")
    def test_extract_date_smart_year(self):
        """Test smart year selection for dates near year boundary."""
        # Today is Jan 6, 2026
        # Jan 9 is in the future -> 2026
        assert extract_date_only("am 9.1.") == "2026-01-09"
        # Jan 3 is 3 days ago (within 7 day window) -> 2026
        assert extract_date_only("am 3.1.") == "2026-01-03"
        # Dec 25 is > 7 days ago -> next year 2026 (but Dec 25 2026 is in future, so stays 2026)
        assert extract_date_only("am 25.12.") == "2026-12-25"


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

    def test_extract_time_validates_hour_range(self):
        """Test that invalid hours (outside 0-23) are rejected."""
        assert extract_time_only("25:00") is None
        assert extract_time_only("24:00") is None
        assert extract_time_only("99 Uhr") is None
        assert extract_time_only("30 uhr") is None
        # Edge cases: 0 and 23 should work
        assert extract_time_only("0:00") == "00:00"
        assert extract_time_only("23:59") == "23:59"

    def test_extract_time_validates_minute_range(self):
        """Test that invalid minutes (outside 0-59) are rejected."""
        assert extract_time_only("10:99") is None
        assert extract_time_only("10:60") is None
        assert extract_time_only("14:75") is None
        # Edge cases: 0 and 59 should work
        assert extract_time_only("10:00") == "10:00"
        assert extract_time_only("10:59") == "10:59"


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


class TestExtractFullName:
    """Tests for extract_full_name function."""

    @pytest.mark.parametrize(
        "text,expected_vorname,expected_nachname",
        [
            # Traditional triggers with two names
            ("Ich heiße Max Mustermann", "Max", "Mustermann"),
            ("ich heisse Anna Schmidt", "Anna", "Schmidt"),
            ("Mein Name ist Thomas Mueller", "Thomas", "Mueller"),
            ("mein name ist Maria Weber", "Maria", "Weber"),
            ("Ich bin Peter Maier", "Peter", "Maier"),
            # Name before email pattern
            ("Britney Spears, theoneandonlybritney@outlook.de", "Britney", "Spears"),
            ("Max Mustermann, max@test.de", "Max", "Mustermann"),
            ("Anna Schmidt anna.schmidt@gmail.com", "Anna", "Schmidt"),
            # Two capitalized words at start
            ("Max Mustermann", "Max", "Mustermann"),
            ("Anna Schmidt möchte ein Probetraining", "Anna", "Schmidt"),
        ],
    )
    def test_extract_full_name_success(self, text: str, expected_vorname: str, expected_nachname: str):
        """Test successful full name extraction from various formats."""
        vorname, nachname = extract_full_name(text)
        assert vorname == expected_vorname
        assert nachname == expected_nachname

    @pytest.mark.parametrize(
        "text",
        [
            "Hallo, wie geht es?",
            "Was kostet das Training?",
            "Termin um 14 Uhr",
            "",
            "ich bin",
            "Ich heiße",
            "max@test.de",  # Only email, no name before it
        ],
    )
    def test_extract_full_name_none(self, text: str):
        """Test that (None, None) is returned when no full name found."""
        vorname, nachname = extract_full_name(text)
        assert vorname is None
        assert nachname is None

    def test_extract_full_name_filters_articles(self):
        """Test that German articles are filtered out."""
        # "der" and "die" should be skipped
        vorname, nachname = extract_full_name("Ich bin der Max Mustermann")
        assert vorname == "Max"
        assert nachname == "Mustermann"

    def test_extract_full_name_only_vorname_with_email(self):
        """Test extraction when only first name before email."""
        vorname, nachname = extract_full_name("Max, max@test.de")
        assert vorname == "Max"
        assert nachname is None

    def test_extract_full_name_nachname_only(self):
        """Test extraction of only last name from 'Mein Nachname ist X'."""
        vorname, nachname = extract_full_name("Mein Nachname ist Mueller")
        assert vorname is None
        assert nachname == "Mueller"

        vorname, nachname = extract_full_name("mein nachname ist Schmidt")
        assert vorname is None
        assert nachname == "Schmidt"

        vorname, nachname = extract_full_name("Nachname ist Weber")
        assert vorname is None
        assert nachname == "Weber"

    def test_extract_full_name_vorname_only(self):
        """Test extraction of only first name from 'Mein Vorname ist X'."""
        vorname, nachname = extract_full_name("Mein Vorname ist Max")
        assert vorname == "Max"
        assert nachname is None

        vorname, nachname = extract_full_name("vorname ist Anna")
        assert vorname == "Anna"
        assert nachname is None

    def test_extract_full_name_rejects_sentence_starts(self):
        """Test that sentence starters are not mistaken for names."""
        # "Ich bin" should not return "Ich" as vorname
        vorname, nachname = extract_full_name("Ich bin interessiert")
        assert vorname is None
        assert nachname is None

    def test_extract_full_name_with_punctuation(self):
        """Test names are cleaned of punctuation."""
        vorname, nachname = extract_full_name("Ich heiße Max Mustermann!")
        assert vorname == "Max"
        assert nachname == "Mustermann"


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
