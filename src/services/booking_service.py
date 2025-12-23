# services/booking_service.py
"""Booking service for MagicLine API integration."""

from typing import Any, Optional

import requests

from config import MAGICLINE_API_KEY, MAGICLINE_BASE_URL, MAGICLINE_BOOKABLE_ID


class BookingService:
    """Handles appointment booking through MagicLine API."""

    def __init__(self):
        self.base_url = MAGICLINE_BASE_URL
        self.api_key = MAGICLINE_API_KEY
        self.bookable_id = MAGICLINE_BOOKABLE_ID
        self.headers = {
            "X-API-KEY": self.api_key,
            "Content-Type": "application/json",
        }

    def validate_slot(
        self, customer_id: int, start_datetime: str, duration_minutes: int = 30
    ) -> dict[str, Any]:
        """
        Validate if appointment slot is available.

        Args:
            customer_id: MagicLine customer ID
            start_datetime: Start time in ISO format
            duration_minutes: Appointment duration (default 20 for EMS)

        Returns:
            Validation response dictionary
        """
        end_datetime = self._calculate_end_time(start_datetime, duration_minutes)

        payload = {
            "customerId": customer_id,
            "bookableAppointmentId": self.bookable_id,
            "startDateTime": start_datetime,
            "endDateTime": end_datetime,
        }

        url = f"{self.base_url}/appointments/bookable/validate"
        print(f"🔍 VALIDATE REQUEST:")
        print(f"   URL: {url}")
        print(f"   Payload: {payload}")

        try:
            response = requests.post(
                url,
                json=payload,
                headers=self.headers,
                timeout=10,
            )
            print(f"   Status: {response.status_code}")
            print(f"   Response: {response.text}")
            return response.json()
        except requests.RequestException as e:
            print(f"   ❌ Error: {e}")
            return {"error": str(e), "validationStatus": "ERROR"}

    def book_appointment(
        self, customer_id: int, start_datetime: str, duration_minutes: int = 30
    ) -> dict[str, Any]:
        """
        Book an appointment slot.

        Args:
            customer_id: MagicLine customer ID
            start_datetime: Start time in ISO format
            duration_minutes: Appointment duration (default 20 for EMS)

        Returns:
            Booking response dictionary with bookingId or error
        """
        end_datetime = self._calculate_end_time(start_datetime, duration_minutes)

        payload = {
            "customerId": customer_id,
            "bookableAppointmentId": self.bookable_id,
            "startDateTime": start_datetime,
            "endDateTime": end_datetime,
        }

        try:
            response = requests.post(
                f"{self.base_url}/appointments/booking/book",
                json=payload,
                headers=self.headers,
                timeout=10,
            )

            if response.status_code == 200:
                return {"success": True, **response.json()}
            else:
                return {"success": False, "error": response.text}

        except requests.RequestException as e:
            return {"success": False, "error": str(e)}

    def try_book(
        self,
        customer_id: int,
        start_datetime: str,
        duration_minutes: int = 30,
    ) -> tuple[bool, str, Optional[str]]:
        """
        Validate and book appointment in one call.

        Args:
            customer_id: MagicLine customer ID
            start_datetime: Start time in ISO format
            duration_minutes: Appointment duration

        Returns:
            Tuple of (success, message, booking_id)
        """
        # First validate
        validation = self.validate_slot(customer_id, start_datetime, duration_minutes)

        if validation.get("validationStatus") != "AVAILABLE":
            return False, "Slot nicht verfügbar – probier ein anderes Datum.", None

        # Then book
        booking = self.book_appointment(customer_id, start_datetime, duration_minutes)

        if booking.get("success"):
            booking_id = booking.get("bookingId")
            return True, "Termin gebucht! Bestätigung per E-Mail unterwegs.", booking_id
        else:
            return False, "Leider nicht verfügbar – wähle ein anderes Datum.", None

    def _calculate_end_time(self, start_datetime: str, duration_minutes: int) -> str:
        """
        Calculate end time from start time and duration.

        Args:
            start_datetime: Start time in ISO format (e.g., 2025-12-26T18:00:00+01:00)
            duration_minutes: Duration in minutes

        Returns:
            End time string in ISO format
        """
        from datetime import datetime, timedelta
        import re

        # Extract the datetime part and timezone
        # Format: 2025-12-26T18:00:00+01:00
        match = re.match(r'(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2})([+-]\d{2}:\d{2})?', start_datetime)
        if not match:
            # Fallback: just return start + duration as simple string
            return start_datetime

        dt_str = match.group(1)
        tz_str = match.group(2) or "+01:00"

        # Parse datetime
        dt = datetime.strptime(dt_str, "%Y-%m-%dT%H:%M:%S")

        # Add duration
        end_dt = dt + timedelta(minutes=duration_minutes)

        # Format back
        return f"{end_dt.strftime('%Y-%m-%dT%H:%M:%S')}{tz_str}"
