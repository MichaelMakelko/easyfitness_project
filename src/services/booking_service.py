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
        self, customer_id: int, start_datetime: str, duration_minutes: int = 20
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

        try:
            response = requests.post(
                f"{self.base_url}/appointments/bookable/validate",
                json=payload,
                headers=self.headers,
                timeout=10,
            )
            return response.json()
        except requests.RequestException as e:
            return {"error": str(e), "validationStatus": "ERROR"}

    def book_appointment(
        self, customer_id: int, start_datetime: str, duration_minutes: int = 20
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
        duration_minutes: int = 20,
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

        Simple implementation - replaces minutes in the time portion.
        For production, use proper datetime parsing.

        Args:
            start_datetime: Start time string
            duration_minutes: Duration in minutes

        Returns:
            End time string
        """
        # Simple replacement for 20-minute EMS sessions
        # In production, use datetime parsing
        return start_datetime.replace("00:00", f"00:{duration_minutes:02d}")
