# services/extraction_service.py
"""Extraction service for LLM-based data extraction from user messages."""

import json
from datetime import datetime, timedelta
from typing import Any, Optional

from constants import validate_email, validate_name


class ExtractionService:
    """Extracts structured data from user messages using LLM."""

    # Note: Dynamic values are inserted at runtime
    EXTRACTION_PROMPT = """Extrahiere aus folgendem Text die Kundendaten.

WICHTIG - Heute ist {weekday}, der {today}.
- morgen = {tomorrow}
- übermorgen = {day_after_tomorrow}

Text: "{text}"

Antworte NUR mit diesem JSON-Format:
{{"vorname": "...", "nachname": "...", "email": "...", "datum": "YYYY-MM-DD", "uhrzeit": "HH:MM"}}

Regeln:
- vorname/nachname: Bei "Mein Name ist X Y" oder "Ich bin X Y" → vorname=X, nachname=Y
- vorname: Bei "Ich bin der X" oder "Ich bin die X" → vorname=X (NICHT "der" oder "die")
- email: Muss @ und . enthalten
- datum: IMMER im Format YYYY-MM-DD
  - "morgen" → {tomorrow}
  - "übermorgen" → {day_after_tomorrow}
  - "nächsten Montag" → berechne das Datum
  - "15.1." → {current_year}-01-15 (oder {next_year} wenn in Vergangenheit)
- uhrzeit: IMMER im Format HH:MM
  - "15 Uhr" → "15:00"
  - "halb 3" → "14:30"
  - "um 10" → "10:00"
- Setze null wenn die Info NICHT im Text steht
- NIEMALS 0000-00-00 oder 1970-01-01 verwenden!"""

    def __init__(self, llm_model: Any):
        """
        Initialize extraction service.

        Args:
            llm_model: LLM model instance with generate_extraction() method
        """
        self.llm = llm_model

    def extract_customer_data(self, text: str) -> dict[str, Optional[str]]:
        """
        Extract customer data (vorname, nachname, email, datum, uhrzeit) from text.

        Args:
            text: User message text

        Returns:
            Dictionary with extracted data, None values for missing fields
        """
        now = datetime.now()
        tomorrow = now + timedelta(days=1)
        day_after = now + timedelta(days=2)

        # German weekday names
        weekdays_de = ["Montag", "Dienstag", "Mittwoch", "Donnerstag", "Freitag", "Samstag", "Sonntag"]

        prompt = self.EXTRACTION_PROMPT.format(
            text=text,
            weekday=weekdays_de[now.weekday()],
            today=now.strftime("%d.%m.%Y"),
            tomorrow=tomorrow.strftime("%Y-%m-%d"),
            day_after_tomorrow=day_after.strftime("%Y-%m-%d"),
            current_year=now.year,
            next_year=now.year + 1,
        )

        messages = [
            {"role": "system", "content": "Du bist ein Daten-Extraktions-Assistent. Antworte nur mit JSON."},
            {"role": "user", "content": prompt}
        ]

        try:
            raw_response = self.llm.generate_extraction(messages)
            print(f"🔍 EXTRACTION RAW: {raw_response[:200]}...")

            extracted = self._parse_extraction_response(raw_response)

            # Validate extracted data
            extracted = self._validate_extracted_data(extracted)

            print(f"🔍 EXTRACTION PARSED & VALIDATED: {extracted}")

            return extracted

        except Exception as e:
            print(f"❌ Extraction error: {e}")
            return {"vorname": None, "nachname": None, "email": None, "datum": None, "uhrzeit": None}

    def _validate_extracted_data(self, data: dict[str, Optional[str]]) -> dict[str, Optional[str]]:
        """
        Validate extracted data and set invalid values to None.

        Args:
            data: Extracted data dictionary

        Returns:
            Validated data dictionary
        """
        # Validate email
        if data.get("email") and not validate_email(data["email"]):
            print(f"⚠️ Invalid email format: {data['email']}")
            data["email"] = None

        # Validate vorname
        if data.get("vorname") and not validate_name(data["vorname"]):
            print(f"⚠️ Invalid vorname: {data['vorname']}")
            data["vorname"] = None

        # Validate nachname
        if data.get("nachname") and not validate_name(data["nachname"]):
            print(f"⚠️ Invalid nachname: {data['nachname']}")
            data["nachname"] = None

        # Validate date format and reasonableness
        if data.get("datum"):
            try:
                parsed_date = datetime.strptime(data["datum"], "%Y-%m-%d")
                now = datetime.now()

                # Reject placeholder dates (before 2020)
                if parsed_date.year < 2020:
                    print(f"⚠️ Placeholder date rejected: {data['datum']}")
                    data["datum"] = None
                # Reject dates more than 1 year in the future
                elif parsed_date > now + timedelta(days=365):
                    print(f"⚠️ Date too far in future: {data['datum']}")
                    data["datum"] = None
                # Reject dates more than 7 days in the past
                elif parsed_date < now - timedelta(days=7):
                    print(f"⚠️ Date too far in past: {data['datum']}")
                    data["datum"] = None
            except ValueError:
                print(f"⚠️ Invalid date format: {data['datum']}")
                data["datum"] = None

        # Validate time format (HH:MM)
        if data.get("uhrzeit"):
            try:
                datetime.strptime(data["uhrzeit"], "%H:%M")
            except ValueError:
                print(f"⚠️ Invalid time format: {data['uhrzeit']}")
                data["uhrzeit"] = None

        return data

    def _parse_extraction_response(self, response: str) -> dict[str, Optional[str]]:
        """
        Parse JSON response from extraction LLM call.

        Args:
            response: Raw LLM response

        Returns:
            Dictionary with extracted data
        """
        result = {"vorname": None, "nachname": None, "email": None, "datum": None, "uhrzeit": None}

        try:
            # Find JSON in response
            start = response.find("{")
            end = response.rfind("}") + 1

            if start != -1 and end > start:
                json_str = response[start:end]
                data = json.loads(json_str)

                # Extract and clean values
                for field in ["vorname", "nachname", "email", "datum", "uhrzeit"]:
                    value = data.get(field)
                    if value and str(value).lower() not in ["null", "none", ""]:
                        result[field] = str(value).strip()

        except json.JSONDecodeError as e:
            print(f"⚠️ JSON parse error: {e}")

        return result
