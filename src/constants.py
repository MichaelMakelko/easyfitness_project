# constants.py
"""Centralized constants, messages, and configuration for the chatbot."""

import re
from collections import OrderedDict
from datetime import datetime, timedelta
from threading import Lock
from typing import Optional

import pytz


# ==================== STUDIO CONFIGURATION ====================
# These can be moved to environment variables for multi-studio support

STUDIO_CONFIG = {
    "name": "easyfitness EMS Packhof Braunschweig",
    "address": "Schild 11, 38100 Braunschweig",
    "hours": "Mo-Fr 9-21 Uhr, Sa 10-16 Uhr",
    "phone": "0531 48039026",
    "email": "ems-braunschweig@easyfitness.club",
    "manager": "Max Dachtler",
    "current_offer": "4 Wochen EMS für nur 99€",
}


# ==================== CUSTOMER STATUS VALUES ====================

class CustomerStatus:
    """Customer status constants."""
    NEW_LEAD = "neuer Interessent"
    NAME_KNOWN = "Name bekannt"
    TRIAL_BOOKED = "Beratungstermin gebucht"  # Changed from "Probetraining gebucht"
    MEMBER = "Mitglied"


# ==================== BOT MESSAGES ====================
# All hardcoded German response strings in one place

class BotMessages:
    """All bot response messages."""

    # Webhook
    WRONG_TOKEN = "Falscher Token"

    # Customer defaults
    DEFAULT_NAME = "du"
    NAME_UNKNOWN = "noch unbekannt"
    NO_PROFILE_DATA = "keine Daten"

    # Booking responses
    BOOKING_SUCCESS = "Termin gebucht! Bestätigung per E-Mail unterwegs."
    BOOKING_SLOT_UNAVAILABLE = "Slot nicht verfügbar - probier ein anderes Datum."
    BOOKING_GENERIC_ERROR = "Leider nicht verfügbar - wähle ein anderes Datum."
    BOOKING_VALIDATION_FAILED = "Deine Daten konnten nicht validiert werden. Bitte überprüfe Name und E-Mail."
    BOOKING_LEAD_CREATION_FAILED = "Lead konnte nicht erstellt werden. Bitte versuche es erneut."
    BOOKING_SERVER_ERROR = "Technisches Problem beim Buchungssystem. Bitte versuche es in ein paar Minuten erneut."
    BOOKING_NETWORK_ERROR = "Verbindungsproblem zum Buchungssystem. Bitte versuche es erneut."

    @staticmethod
    def slot_unavailable_with_alternatives(alternatives: list[str]) -> str:
        """
        Message when requested slot is not available but alternatives exist.

        Args:
            alternatives: List of alternative time slots in HH:MM format

        Returns:
            German message suggesting alternative times
        """
        if not alternatives:
            return BotMessages.BOOKING_SLOT_UNAVAILABLE

        # Format alternatives with "Uhr" suffix
        formatted = [f"{time} Uhr" for time in alternatives]

        if len(formatted) == 1:
            return f"Diese Zeit ist leider belegt. Wie wäre es um {formatted[0]}?"
        elif len(formatted) == 2:
            return f"Diese Zeit ist leider belegt. Verfügbar wäre: {formatted[0]} oder {formatted[1]}."
        else:
            last = formatted[-1]
            rest = ", ".join(formatted[:-1])
            return f"Diese Zeit ist leider belegt. Verfügbar wäre: {rest} oder {last}."

    # Missing data prompts
    @staticmethod
    def missing_time(date_german: str) -> str:
        """Prompt when time is missing for booking."""
        return f"Um welche Uhrzeit möchtest du am {date_german} vorbeikommen? 🕐"

    @staticmethod
    def missing_booking_data(fields: list[str]) -> str:
        """Prompt when required booking data is missing."""
        fields_str = ", ".join(fields)
        return f"Um deinen Termin zu buchen, brauche ich noch: {fields_str}. Kannst du mir diese Infos geben? 📝"

    # Support escalation
    @staticmethod
    def support_escalation() -> str:
        """Message for complaints/cancellation requests."""
        phone = STUDIO_CONFIG["phone"]
        email = STUDIO_CONFIG["email"]
        return f"Für Vertragsangelegenheiten wende dich bitte an: {phone} oder {email} 📞"

    @staticmethod
    def complaint_response() -> str:
        """Message for customer complaints."""
        phone = STUDIO_CONFIG["phone"]
        email = STUDIO_CONFIG["email"]
        return f"Das tut mir leid. Ruf uns gerne direkt an: {phone} oder schreib an {email} 📞"


# ==================== TIMEZONE HANDLING ====================

TIMEZONE = "Europe/Berlin"


def get_timezone_offset() -> str:
    """
    Get current timezone offset for Germany (handles CET/CEST automatically).

    Returns:
        Timezone offset string like "+01:00" (winter) or "+02:00" (summer)
    """
    try:
        tz = pytz.timezone(TIMEZONE)
        now = datetime.now(tz)
        offset = now.strftime('%z')  # Returns "+0100" or "+0200"
        # Format as "+01:00" instead of "+0100"
        return f"{offset[:3]}:{offset[3:]}"
    except Exception:
        # Fallback to CET if pytz fails
        return "+01:00"


def get_current_datetime_iso() -> str:
    """Get current datetime in ISO format with correct timezone."""
    try:
        tz = pytz.timezone(TIMEZONE)
        now = datetime.now(tz)
        return now.isoformat()
    except Exception:
        # Fallback to naive datetime if pytz fails
        return datetime.now().isoformat()


# ==================== VALIDATION UTILITIES ====================

EMAIL_PATTERN = re.compile(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$')
PHONE_PATTERN = re.compile(r'^[0-9+\s\-()]{7,20}$')


def validate_email(email: Optional[str]) -> bool:
    """
    Validate email address format.

    Args:
        email: Email address to validate

    Returns:
        True if valid email format, False otherwise
    """
    if not email:
        return False
    return bool(EMAIL_PATTERN.match(email.strip()))


def validate_phone(phone: Optional[str]) -> bool:
    """
    Validate phone number format.

    Args:
        phone: Phone number to validate

    Returns:
        True if valid phone format, False otherwise
    """
    if not phone:
        return False
    return bool(PHONE_PATTERN.match(phone.strip()))


def validate_name(name: Optional[str]) -> bool:
    """
    Validate name (not empty, not just articles, reasonable length).

    Args:
        name: Name to validate

    Returns:
        True if valid name, False otherwise
    """
    if not name:
        return False

    name = name.strip().lower()

    # Must be at least 2 characters
    if len(name) < 2:
        return False

    # Must not be just an article or common word
    invalid_names = {"der", "die", "das", "ich", "du", "und", "oder", "ein", "eine"}
    if name in invalid_names:
        return False

    # Must contain at least one letter
    if not any(c.isalpha() for c in name):
        return False

    return True


# ==================== DATE UTILITIES ====================

def parse_date_smart(day: int, month: int, year: Optional[int] = None) -> Optional[str]:
    """
    Parse date components into YYYY-MM-DD format, assuming future dates.

    If no year provided, uses current year. If resulting date is more than
    7 days in the past, assumes next year.

    Args:
        day: Day of month (1-31)
        month: Month (1-12)
        year: Year (optional, defaults to current/next year)

    Returns:
        Date string in YYYY-MM-DD format, or None if invalid date
    """
    today = datetime.now()

    if year is None:
        year = today.year

    try:
        candidate = datetime(year, month, day)

        # If date is more than 7 days in the past, assume next year
        if candidate < today - timedelta(days=7):
            candidate = datetime(year + 1, month, day)

        return candidate.strftime("%Y-%m-%d")
    except ValueError:
        # Invalid date (e.g., Feb 30)
        return None


def format_date_german(date_str: str) -> str:
    """
    Format YYYY-MM-DD to German DD.MM.YYYY format.

    Args:
        date_str: Date in YYYY-MM-DD format

    Returns:
        Date in DD.MM.YYYY format
    """
    try:
        year, month, day = date_str.split("-")
        return f"{day}.{month}.{year}"
    except (ValueError, AttributeError):
        return date_str


def build_datetime_iso(datum: Optional[str], uhrzeit: Optional[str]) -> Optional[str]:
    """
    Build ISO 8601 datetime string with correct timezone.

    Args:
        datum: Date in YYYY-MM-DD format
        uhrzeit: Time in HH:MM format

    Returns:
        ISO 8601 datetime string or None if incomplete
    """
    if datum and uhrzeit:
        tz_offset = get_timezone_offset()
        return f"{datum}T{uhrzeit}:00{tz_offset}"
    return None


# ==================== DUPLICATE MESSAGE HANDLING ====================


class ProcessedMessageTracker:
    """
    Thread-safe tracker for processed message IDs with LRU eviction.

    Prevents duplicate message processing while maintaining bounded memory.
    """

    def __init__(self, max_size: int = 1000):
        self._messages: OrderedDict[str, bool] = OrderedDict()
        self._max_size = max_size
        self._lock = Lock()

    def is_duplicate(self, msg_id: str) -> bool:
        """
        Check if message was already processed.

        Args:
            msg_id: WhatsApp message ID

        Returns:
            True if already processed (duplicate), False if new
        """
        with self._lock:
            if msg_id in self._messages:
                return True

            # Add new message
            self._messages[msg_id] = True

            # Evict oldest if over limit (LRU eviction)
            while len(self._messages) > self._max_size:
                self._messages.popitem(last=False)

            return False

    def clear(self) -> None:
        """Clear all tracked messages."""
        with self._lock:
            self._messages.clear()

    def __len__(self) -> int:
        """Return number of tracked messages (thread-safe)."""
        with self._lock:
            return len(self._messages)


# Global instance for message tracking
message_tracker = ProcessedMessageTracker(max_size=1000)
