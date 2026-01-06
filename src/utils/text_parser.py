# utils/text_parser.py
"""Text parsing utilities for extracting information from messages."""

import re
from datetime import datetime, timedelta
from typing import Optional


def extract_name(text: str) -> Optional[str]:
    """
    Extract customer first name from message text.

    Looks for common German phrases like "ich heiße", "mein name ist", etc.

    Args:
        text: The message text to parse

    Returns:
        Extracted first name or None if not found
    """
    lower = text.lower()
    # Support both "ß" and "ss" spelling for German
    triggers = ["ich heiße", "ich heisse", "mein name ist", "bin der ", "bin die ", "ich bin "]

    for trigger in triggers:
        if trigger in lower:
            remaining = lower.split(trigger)[-1].strip().split()
            if not remaining:
                continue
            candidate = remaining[0].capitalize()
            if 2 <= len(candidate) <= 20 and candidate.lower() not in ["ich", "der", "die", "und"]:
                return candidate
    return None


def extract_full_name(text: str) -> tuple[Optional[str], Optional[str]]:
    """
    Extract full name (vorname and nachname) from message text.

    Supports various formats:
    - "Ich heiße Max Mustermann"
    - "Mein Name ist Anna Schmidt"
    - "Mein Nachname ist Schmidt" (only last name)
    - "Mein Vorname ist Max" (only first name)
    - "Max Mustermann, max@email.de" (name before comma+email)
    - "Vorname Nachname" (two capitalized words at start)

    Args:
        text: The message text to parse

    Returns:
        Tuple of (vorname, nachname), either can be None
    """
    lower = text.lower()

    # Pattern 0: Explicit "Nachname ist X" or "Vorname ist X" (single name extraction)
    # This MUST come first to avoid "Mein" being extracted as vorname
    nachname_match = re.search(r'(?:mein\s+)?nachname\s+(?:ist\s+)?(\w+)', lower)
    if nachname_match:
        nachname = nachname_match.group(1)
        if _is_valid_name(nachname):
            return None, nachname.capitalize()

    vorname_match = re.search(r'(?:mein\s+)?vorname\s+(?:ist\s+)?(\w+)', lower)
    if vorname_match:
        vorname = vorname_match.group(1)
        if _is_valid_name(vorname):
            return vorname.capitalize(), None

    # Pattern 1: Traditional triggers with two names
    triggers = [
        ("ich heiße ", 2),
        ("ich heisse ", 2),
        ("mein name ist ", 2),
        ("ich bin ", 2),
    ]

    for trigger, min_words in triggers:
        if trigger in lower:
            # Get the part after the trigger
            idx = lower.index(trigger)
            remaining = text[idx + len(trigger):].strip()
            words = remaining.split()

            if len(words) >= 2:
                # Filter out articles and common words
                skip_words = {"der", "die", "das", "ein", "eine", "und", "oder"}
                clean_words = [w for w in words[:3] if w.lower() not in skip_words]

                if len(clean_words) >= 2:
                    vorname = clean_words[0].strip(",.!?")
                    nachname = clean_words[1].strip(",.!?")
                    if _is_valid_name(vorname) and _is_valid_name(nachname):
                        return vorname.capitalize(), nachname.capitalize()

    # Pattern 2: "Vorname Nachname, email@domain.de" or "Vorname Nachname email@domain.de"
    email_match = re.search(r'[\w\.-]+@[\w\.-]+\.\w+', text)
    if email_match:
        # Get text before the email
        before_email = text[:email_match.start()].strip().rstrip(",").strip()
        words = before_email.split()

        if len(words) >= 2:
            # Take last two words before email as name
            vorname = words[-2].strip(",.!?")
            nachname = words[-1].strip(",.!?")
            if _is_valid_name(vorname) and _is_valid_name(nachname):
                return vorname.capitalize(), nachname.capitalize()
        elif len(words) == 1:
            # Only one word, could be just vorname
            vorname = words[0].strip(",.!?")
            if _is_valid_name(vorname):
                return vorname.capitalize(), None

    # Pattern 3: Two capitalized words at the start (looks like a name)
    words = text.split()
    if len(words) >= 2:
        first_word = words[0].strip(",.!?")
        second_word = words[1].strip(",.!?")

        # Both words should start with uppercase and be valid names
        if (first_word and first_word[0].isupper() and
            second_word and second_word[0].isupper() and
            _is_valid_name(first_word) and _is_valid_name(second_word)):
            # Make sure it's not a sentence start
            if second_word.lower() not in {"ist", "bin", "habe", "möchte", "will", "kann", "heiße", "heisse"}:
                return first_word, second_word

    return None, None


def _is_valid_name(name: str) -> bool:
    """Check if a string looks like a valid name."""
    if not name or len(name) < 2 or len(name) > 30:
        return False
    # Name should be mostly letters
    letter_count = sum(1 for c in name if c.isalpha())
    return letter_count >= len(name) * 0.8


def extract_booking_intent(text: str, reply: str, customer_context: dict = None) -> bool:
    """
    Detect if a booking/appointment is being requested.

    Uses keyword matching plus optional customer context for multi-message booking flows.

    Args:
        text: Customer message
        reply: Bot reply
        customer_context: Optional dict with 'has_booking_data' (name+email present)
                         and 'has_partial_datetime' (datum or uhrzeit in profile)

    Returns:
        True if booking intent detected
    """
    combined = (text + reply).lower()

    # Buchungs-Keywords (eines davon reicht) - erweitert für LLM-Varianten
    # NOTE: "kommen" removed - too generic, causes false positives like "kann nicht kommen"
    booking_keywords = [
        "probetraining", "probentraining", "probe training",  # inkl. LLM-Variante
        "termin", "buchen", "buchung", "gebucht",
        "anmelden", "anmeldung", "reservieren", "reservierung",
        "training machen", "training buchen",
        "vorbeikommen", "vorbei kommen",  # "kommen" allein zu generisch
        "ausprobieren", "testen", "probieren",
        "einbuchen", "eintragen",
    ]
    has_booking_keyword = any(kw in combined for kw in booking_keywords)

    # Datumserkennung (verschiedene Formate)
    has_date = bool(
        re.search(r'\d{1,2}\.\d{1,2}\.\d{2,4}', combined) or  # DD.MM.YYYY oder DD.MM.YY
        re.search(r'\d{1,2}\.\d{1,2}\.', combined) or  # DD.MM.
        re.search(r'(?:am|den|vom|bis|ab)\s*\d{1,2}\.\d{1,2}(?!\d|\.)', combined) or  # "am 9.1"
        re.search(r'\d{1,2}\.\d{1,2}\s*(?:um|uhr|kommen|gehen)', combined) or  # "9.1 um 10"
        re.search(r'(montag|dienstag|mittwoch|donnerstag|freitag|samstag|sonntag)', combined) or
        re.search(r'(morgen|übermorgen|nächste woche|diese woche)', combined)
    )

    # Uhrzeiterkennung
    has_time = bool(
        re.search(r'\d{1,2}:\d{2}', combined) or  # HH:MM
        re.search(r'\d{1,2}\s*uhr', combined)  # X Uhr
    )

    # Standard check: keyword + (date or time)
    if has_booking_keyword and (has_date or has_time):
        return True

    # Context-aware check: If customer is in booking flow (has name+email)
    # and provides date/time, assume booking intent even without keyword
    if customer_context:
        has_booking_data = customer_context.get("has_booking_data", False)
        has_partial_datetime = customer_context.get("has_partial_datetime", False)

        # Customer already in booking flow + provides date or time
        if has_booking_data and (has_date or has_time):
            return True

        # Customer has partial booking (e.g., date stored) + provides time
        if has_partial_datetime and (has_date or has_time):
            return True

    return False


def extract_date_only(text: str) -> Optional[str]:
    """
    Extract only date from text in German format.

    Supports:
    - DD.MM.YYYY (e.g., "25.12.2026")
    - DD.MM. (e.g., "25.12.")
    - DD.MM (e.g., "9.1" or "am 9.1") - common German short format
    - "am DD.MM" context (e.g., "am 9.1 kommen")
    - "morgen" / "übermorgen" - relative dates

    Args:
        text: Text to parse

    Returns:
        Date string in YYYY-MM-DD format or None
    """
    now = datetime.now()
    lower = text.lower()

    # Check for relative date expressions FIRST (most reliable)
    if re.search(r'\bmorgen\b', lower) and not re.search(r'\bübermorgen\b', lower):
        # "morgen" but NOT "übermorgen"
        tomorrow = now + timedelta(days=1)
        return tomorrow.strftime("%Y-%m-%d")

    if re.search(r'\bübermorgen\b', lower):
        day_after = now + timedelta(days=2)
        return day_after.strftime("%Y-%m-%d")

    # Try full date DD.MM.YYYY
    date_match = re.search(r'(\d{1,2})\.(\d{1,2})\.(\d{4})', text)
    if date_match:
        day, month, year = date_match.groups()
        return f"{year}-{month.zfill(2)}-{day.zfill(2)}"

    # Try short date DD.MM. (with trailing dot)
    short_date_dot = re.search(r'(\d{1,2})\.(\d{1,2})\.(?!\d)', text)
    if short_date_dot:
        day, month = short_date_dot.groups()
        return _build_date_with_smart_year(int(day), int(month), now)

    # Try DD.MM without trailing dot - look for context like "am 9.1" or "9.1 um"
    # This avoids matching decimal numbers like "1.5 Stunden"
    short_date_context = re.search(
        r'(?:am|den|vom|bis|ab)\s*(\d{1,2})\.(\d{1,2})(?!\d|\.)|'  # "am 9.1", "den 15.3"
        r'(\d{1,2})\.(\d{1,2})\s*(?:um|uhr|kommen|gehen|möchte)',  # "9.1 um 10 Uhr"
        text.lower()
    )
    if short_date_context:
        groups = short_date_context.groups()
        # Groups are (day1, month1, day2, month2) - pick the non-None pair
        if groups[0] and groups[1]:
            day, month = groups[0], groups[1]
        else:
            day, month = groups[2], groups[3]
        return _build_date_with_smart_year(int(day), int(month), now)

    return None


def _build_date_with_smart_year(day: int, month: int, now: datetime) -> Optional[str]:
    """
    Build date string with smart year selection.

    If the date would be more than 7 days in the past, assume next year.

    Args:
        day: Day of month
        month: Month number
        now: Current datetime

    Returns:
        Date string in YYYY-MM-DD format or None if invalid
    """
    year = now.year

    try:
        candidate = datetime(year, month, day)

        # If date is more than 7 days in the past, assume next year
        if candidate < now - timedelta(days=7):
            candidate = datetime(year + 1, month, day)

        return candidate.strftime("%Y-%m-%d")
    except ValueError:
        # Invalid date (e.g., Feb 30)
        return None


def extract_time_only(text: str) -> Optional[str]:
    """
    Extract only time from text.

    Supports:
    - HH:MM (validates 0-23 hours, 0-59 minutes)
    - "X Uhr" format (validates 0-23 hours)

    Args:
        text: Text to parse

    Returns:
        Time string in HH:MM format or None
    """
    # Try HH:MM format
    time_match = re.search(r'(\d{1,2}):(\d{2})', text)
    if time_match:
        hour_str, minute_str = time_match.groups()
        hour = int(hour_str)
        minute = int(minute_str)
        # Validate hour (0-23) and minute (0-59)
        if 0 <= hour <= 23 and 0 <= minute <= 59:
            return f"{hour_str.zfill(2)}:{minute_str}"
        # Invalid time, continue to next pattern or return None

    # Try "X Uhr" format
    uhr_match = re.search(r'(\d{1,2})\s*uhr', text.lower())
    if uhr_match:
        hour_str = uhr_match.group(1)
        hour = int(hour_str)
        # Validate hour (0-23)
        if 0 <= hour <= 23:
            return f"{hour_str.zfill(2)}:00"

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
    from constants import get_timezone_offset

    date = extract_date_only(text)
    time = extract_time_only(text)

    if date and time:
        tz_offset = get_timezone_offset()
        return f"{date}T{time}:00{tz_offset}"

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
