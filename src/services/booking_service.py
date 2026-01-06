# services/booking_service.py
"""Booking service for MagicLine API integration."""

from typing import Any, Optional

import requests

from config import (
    MAGICLINE_API_KEY,
    MAGICLINE_BASE_URL,
    MAGICLINE_BOOKABLE_ID,
    MAGICLINE_TRIAL_OFFER_CONFIG_ID,
)
from constants import BotMessages


class BookingService:
    """Handles appointment booking through MagicLine API."""

    def __init__(self):
        self.base_url = MAGICLINE_BASE_URL
        self.api_key = MAGICLINE_API_KEY
        self.bookable_id = MAGICLINE_BOOKABLE_ID
        self.trial_offer_config_id = MAGICLINE_TRIAL_OFFER_CONFIG_ID
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
            return False, BotMessages.BOOKING_SLOT_UNAVAILABLE, None

        # Then book
        booking = self.book_appointment(customer_id, start_datetime, duration_minutes)

        if booking.get("success"):
            booking_id = booking.get("bookingId")
            return True, BotMessages.BOOKING_SUCCESS, booking_id
        else:
            return False, BotMessages.BOOKING_GENERIC_ERROR, None

    # ==================== TRIAL OFFER METHODS (für nicht-registrierte Leads) ====================

    def validate_lead(
        self, first_name: str, last_name: str, email: str
    ) -> dict[str, Any]:
        """
        Validate lead data before creating.

        Args:
            first_name: Lead's first name
            last_name: Lead's last name
            email: Lead's email address

        Returns:
            Validation response dictionary
        """
        payload = {
            "leadCustomerData": {
                "firstname": first_name,
                "lastname": last_name,
                "email": email,
            },
            "trialOfferConfigId": self.trial_offer_config_id,
        }

        url = f"{self.base_url}/trial-offers/lead/validate"
        print(f"🔍 VALIDATE LEAD REQUEST:")
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

            if response.status_code == 200:
                return {"success": True, **response.json()}
            else:
                return {"success": False, "error": response.text}
        except requests.RequestException as e:
            print(f"   ❌ Error: {e}")
            return {"success": False, "error": str(e)}

    def create_lead(
        self, first_name: str, last_name: str, email: str
    ) -> dict[str, Any]:
        """
        Create a new lead in MagicLine.

        Args:
            first_name: Lead's first name
            last_name: Lead's last name
            email: Lead's email address

        Returns:
            Response dictionary with leadCustomerId or error
        """
        payload = {
            "leadCustomerData": {
                "firstname": first_name,
                "lastname": last_name,
                "email": email,
            },
            "trialOfferConfigId": self.trial_offer_config_id,
        }

        url = f"{self.base_url}/trial-offers/lead/create"
        print(f"📝 CREATE LEAD REQUEST:")
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

            if response.status_code == 200:
                return {"success": True, **response.json()}
            else:
                return {"success": False, "error": response.text}
        except requests.RequestException as e:
            print(f"   ❌ Error: {e}")
            return {"success": False, "error": str(e)}

    def validate_appointment_for_lead(
        self,
        lead_customer_id: int,
        start_datetime: str,
        duration_minutes: int = 30,
    ) -> dict[str, Any]:
        """
        Validate appointment slot for a lead customer.

        Uses the regular appointment validation endpoint with leadCustomerId.

        Args:
            lead_customer_id: Lead customer ID from create_lead
            start_datetime: Start time in ISO format
            duration_minutes: Appointment duration

        Returns:
            Validation response dictionary
        """
        end_datetime = self._calculate_end_time(start_datetime, duration_minutes)

        payload = {
            "customerId": lead_customer_id,
            "bookableAppointmentId": self.bookable_id,
            "startDateTime": start_datetime,
            "endDateTime": end_datetime,
        }

        url = f"{self.base_url}/appointments/bookable/validate"
        print(f"🔍 VALIDATE APPOINTMENT FOR LEAD REQUEST:")
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

            if response.status_code == 200:
                return {"success": True, **response.json()}
            else:
                return {"success": False, "error": response.text}
        except requests.RequestException as e:
            print(f"   ❌ Error: {e}")
            return {"success": False, "error": str(e)}

    def book_appointment_for_lead(
        self,
        lead_customer_id: int,
        start_datetime: str,
        duration_minutes: int = 30,
    ) -> dict[str, Any]:
        """
        Book an appointment for a lead customer.

        Uses the regular appointment booking endpoint with leadCustomerId.

        Args:
            lead_customer_id: Lead customer ID from create_lead
            start_datetime: Start time in ISO format
            duration_minutes: Appointment duration

        Returns:
            Booking response dictionary with bookingId or error
        """
        end_datetime = self._calculate_end_time(start_datetime, duration_minutes)

        payload = {
            "customerId": lead_customer_id,
            "bookableAppointmentId": self.bookable_id,
            "startDateTime": start_datetime,
            "endDateTime": end_datetime,
        }

        url = f"{self.base_url}/appointments/booking/book"
        print(f"📅 BOOK APPOINTMENT FOR LEAD REQUEST:")
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

            if response.status_code == 200:
                return {"success": True, **response.json()}
            else:
                return {"success": False, "error": response.text}
        except requests.RequestException as e:
            print(f"   ❌ Error: {e}")
            return {"success": False, "error": str(e)}

    def try_book_trial_offer(
        self,
        first_name: str,
        last_name: str,
        email: str,
        start_datetime: str,
        duration_minutes: int = 30,
    ) -> tuple[bool, str, Optional[str]]:
        """
        Complete trial offer booking flow for unregistered leads.

        Steps:
        1. Validate lead data
        2. Create lead in MagicLine → get leadCustomerId
        3. Validate booking slot with leadCustomerId
        4. Book the appointment with leadCustomerId

        Args:
            first_name: Lead's first name
            last_name: Lead's last name
            email: Lead's email address
            start_datetime: Start time in ISO format
            duration_minutes: Appointment duration

        Returns:
            Tuple of (success, message, booking_id)
        """
        print(f"🎯 TRIAL OFFER BOOKING FLOW START")
        print(f"   Name: {first_name} {last_name}")
        print(f"   Email: {email}")
        print(f"   DateTime: {start_datetime}")

        # Step 1: Validate lead
        lead_validation = self.validate_lead(first_name, last_name, email)
        if not lead_validation.get("success"):
            error = lead_validation.get("error", "Unbekannter Fehler")
            print(f"   ❌ Lead-Validierung fehlgeschlagen: {error}")
            return False, BotMessages.BOOKING_VALIDATION_FAILED, None

        # Step 2: Create lead → get leadCustomerId
        lead_creation = self.create_lead(first_name, last_name, email)
        if not lead_creation.get("success"):
            error = lead_creation.get("error", "Unbekannter Fehler")
            print(f"   ❌ Lead-Erstellung fehlgeschlagen: {error}")
            return False, BotMessages.BOOKING_LEAD_CREATION_FAILED, None

        lead_customer_id = lead_creation.get("leadCustomerId")
        if not lead_customer_id:
            print(f"   ❌ Keine leadCustomerId erhalten")
            return False, BotMessages.BOOKING_LEAD_CREATION_FAILED, None

        print(f"   ✅ Lead erstellt mit ID: {lead_customer_id}")

        # Step 3: Validate booking slot with leadCustomerId
        booking_validation = self.validate_appointment_for_lead(
            lead_customer_id, start_datetime, duration_minutes
        )
        if not booking_validation.get("success"):
            error = booking_validation.get("error", "Unbekannter Fehler")
            print(f"   ❌ Slot-Validierung fehlgeschlagen: {error}")
            return False, BotMessages.BOOKING_SLOT_UNAVAILABLE, None

        # Check validation status
        validation_status = booking_validation.get("validationStatus")
        if validation_status != "AVAILABLE":
            print(f"   ❌ Slot nicht verfügbar: {validation_status}")
            return False, BotMessages.BOOKING_SLOT_UNAVAILABLE, None

        # Step 4: Book appointment with leadCustomerId
        booking = self.book_appointment_for_lead(
            lead_customer_id, start_datetime, duration_minutes
        )
        if booking.get("success"):
            booking_id = booking.get("bookingId")
            print(f"   ✅ Buchung erfolgreich! Booking-ID: {booking_id}")
            return True, BotMessages.BOOKING_SUCCESS, booking_id
        else:
            error = booking.get("error", "Unbekannter Fehler")
            print(f"   ❌ Buchung fehlgeschlagen: {error}")
            return False, BotMessages.BOOKING_GENERIC_ERROR, None

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
