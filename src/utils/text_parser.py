# utils/text_parser.py
"""Text parsing utilities for extracting information from messages."""

import re
from typing import Optional


def extract_name(text: str) -> Optional[str]:
    """
    Extract customer name from message text.

    Looks for common German phrases like "ich heiße", "mein name ist", etc.

    Args:
        text: The message text to parse

    Returns:
        Extracted name or None if not found
    """
    lower = text.lower()
    triggers = ["ich heiße", "mein name ist", "bin der ", "bin die ", "ich bin "]

    for trigger in triggers:
        if trigger in lower:
            candidate = lower.split(trigger)[-1].strip().split()[0].capitalize()
            if 2 <= len(candidate) <= 20 and candidate.lower() not in ["ich", "der", "die", "und"]:
                return candidate
    return None


def extract_booking_intent(text: str, reply: str) -> bool:
    """
    Detect if a booking/appointment is being requested.

    Args:
        text: Customer message
        reply: Bot reply

    Returns:
        True if booking intent detected
    """
    combined = (text + reply).lower()
    has_probetraining = "probetraining" in combined
    has_termin = "termin" in combined
    has_date = bool(re.search(r'\d{2}\.\d{2}\.\d{4}', combined))

    return has_probetraining and has_termin and has_date


def extract_date_time(text: str) -> Optional[str]:
    """
    Extract date and time from text in German format.

    Expects format: DD.MM.YYYY and HH:MM

    Args:
        text: Text to parse (should be lowercased)

    Returns:
        ISO 8601 formatted datetime string or None
    """
    date_match = re.search(r'(\d{2})\.(\d{2})\.(\d{4})', text)
    time_match = re.search(r'(\d{2}):(\d{2})', text)

    if date_match and time_match:
        day, month, year = date_match.groups()
        hour, minute = time_match.groups()
        return f"{year}-{month}-{day}T{hour}:{minute}:00+01:00[Europe/Berlin]"
    return None


def extract_email(text: str) -> Optional[str]:
    """
    Extract email address from text.

    Args:
        text: Text to parse

    Returns:
        Email address or None
    """
    match = re.search(r'[\w\.-]+@[\w\.-]+\.\w+', text.lower())
    return match.group(0) if match else None
