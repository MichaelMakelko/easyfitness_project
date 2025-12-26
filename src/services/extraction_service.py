# services/extraction_service.py
"""Extraction service for LLM-based data extraction from user messages."""

import json
from datetime import datetime
from typing import Any, Optional


class ExtractionService:
    """Extracts structured data from user messages using LLM."""

    EXTRACTION_PROMPT = """Extrahiere aus folgendem Text die Kundendaten.

Heute ist {today}.

Text: "{text}"

Antworte NUR mit JSON, nichts anderes:
{{"vorname": "...", "nachname": "...", "email": "...", "datum": "YYYY-MM-DD", "uhrzeit": "HH:MM"}}

Regeln:
- Bei "Mein Name ist X Y" oder "Ich bin X Y" → vorname=X, nachname=Y
- Beispiel: "Mein Name ist Michael Makelko" → "vorname": "Michael", "nachname": "Makelko"
- Beispiel: "Ich bin Anna Schmidt" → "vorname": "Anna", "nachname": "Schmidt"
- Email = E-Mail-Adresse
- Datum im Format YYYY-MM-DD (z.B. "30.12" → "2025-12-30")
- Uhrzeit im Format HH:MM (z.B. "14 Uhr" → "14:00")
- Setze null NUR wenn die Info wirklich NICHT im Text steht"""

    def __init__(self, llm_model: Any):
        """
        Initialize extraction service.

        Args:
            llm_model: LLM model instance with generate() method
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
        today = datetime.now().strftime("%d.%m.%Y")
        prompt = self.EXTRACTION_PROMPT.format(text=text, today=today)

        messages = [
            {"role": "system", "content": "Du bist ein Daten-Extraktions-Assistent. Antworte nur mit JSON."},
            {"role": "user", "content": prompt}
        ]

        try:
            raw_response = self.llm.generate(messages)
            print(f"🔍 EXTRACTION RAW: {raw_response[:200]}...")

            extracted = self._parse_extraction_response(raw_response)
            print(f"🔍 EXTRACTION PARSED: {extracted}")

            return extracted

        except Exception as e:
            print(f"❌ Extraction error: {e}")
            return {"vorname": None, "nachname": None, "email": None, "datum": None, "uhrzeit": None}

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

    def build_datetime_iso(self, datum: Optional[str], uhrzeit: Optional[str]) -> Optional[str]:
        """
        Build ISO 8601 datetime string from extracted date and time.

        Args:
            datum: Date in YYYY-MM-DD format
            uhrzeit: Time in HH:MM format

        Returns:
            ISO 8601 datetime string or None if incomplete
        """
        if datum and uhrzeit:
            return f"{datum}T{uhrzeit}:00+01:00"
        return None
