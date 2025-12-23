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

    # Buchungs-Keywords (eines davon reicht)
    booking_keywords = [
        "probetraining", "probe training", "termin", "buchen", "buchung",
        "anmelden", "anmeldung", "reservieren", "training machen",
        "vorbeikommen", "ausprobieren"
    ]
    has_booking_keyword = any(kw in combined for kw in booking_keywords)

    # Datumserkennung (verschiedene Formate)
    has_date = bool(
        re.search(r'\d{1,2}\.\d{1,2}\.\d{2,4}', combined) or  # DD.MM.YYYY oder DD.MM.YY
        re.search(r'\d{1,2}\.\d{1,2}\.', combined) or  # DD.MM.
        re.search(r'(montag|dienstag|mittwoch|donnerstag|freitag|samstag|sonntag)', combined) or
        re.search(r'(morgen|übermorgen|nächste woche|diese woche)', combined)
    )

    # Uhrzeiterkennung
    has_time = bool(
        re.search(r'\d{1,2}:\d{2}', combined) or  # HH:MM
        re.search(r'\d{1,2}\s*uhr', combined)  # X Uhr
    )

    return has_booking_keyword and (has_date or has_time)


def extract_date_only(text: str) -> Optional[str]:
    """
    Extract only date from text in German format.

    Supports:
    - DD.MM.YYYY
    - DD.MM. (assumes current year)

    Args:
        text: Text to parse

    Returns:
        Date string in YYYY-MM-DD format or None
    """
    from datetime import datetime

    # Try full date DD.MM.YYYY
    date_match = re.search(r'(\d{1,2})\.(\d{1,2})\.(\d{4})', text)

    # Try short date DD.MM. (without year - assumes current year)
    if not date_match:
        short_date = re.search(r'(\d{1,2})\.(\d{1,2})\.', text)
        if short_date:
            day, month = short_date.groups()
            year = str(datetime.now().year)
            return f"{year}-{month.zfill(2)}-{day.zfill(2)}"

    if date_match:
        day, month, year = date_match.groups()
        return f"{year}-{month.zfill(2)}-{day.zfill(2)}"

    return None


def extract_time_only(text: str) -> Optional[str]:
    """
    Extract only time from text.

    Supports:
    - HH:MM
    - "X Uhr" format

    Args:
        text: Text to parse

    Returns:
        Time string in HH:MM format or None
    """
    # Try HH:MM format
    time_match = re.search(r'(\d{1,2}):(\d{2})', text)
    if time_match:
        hour, minute = time_match.groups()
        return f"{hour.zfill(2)}:{minute}"

    # Try "X Uhr" format
    uhr_match = re.search(r'(\d{1,2})\s*uhr', text.lower())
    if uhr_match:
        hour = uhr_match.group(1)
        return f"{hour.zfill(2)}:00"

    return None


def extract_date_time(text: str) -> Optional[str]:
    """
    Extract date and time from text in German format.

    Only returns a value if BOTH date AND time are present.

    Args:
        text: Text to parse

    Returns:
        ISO 8601 formatted datetime string or None
    """
    date = extract_date_only(text)
    time = extract_time_only(text)

    if date and time:
        return f"{date}T{time}:00+01:00"

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
