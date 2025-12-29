"""Integration tests for complete booking flow."""

import pytest
import responses
from unittest.mock import MagicMock, patch

from services.booking_service import BookingService
from services.customer_service import CustomerService
from services.extraction_service import ExtractionService
from utils.text_parser import extract_booking_intent


class TestBookingIntentDetection:
    """Integration tests for booking intent detection."""

    def test_intent_with_probetraining_and_date(self):
        """Test booking intent with 'probetraining' keyword and date."""
        assert extract_booking_intent("Probetraining am 20.01.2025", "") is True

    def test_intent_with_termin_and_weekday(self):
        """Test booking intent with 'termin' keyword and weekday."""
        assert extract_booking_intent("Termin am Montag", "") is True

    def test_intent_with_buchen_and_time(self):
        """Test booking intent with 'buchen' keyword and time."""
        assert extract_booking_intent("Buchen um 14:00", "") is True

    def test_intent_keyword_in_reply(self):
        """Test booking intent when keyword is in bot reply."""
        assert extract_booking_intent("am 20.01.", "Probetraining") is True

    def test_no_intent_without_date_or_time(self):
        """Test no booking intent without date/time."""
        assert extract_booking_intent("Ich moechte ein Probetraining", "") is False

    def test_no_intent_without_keyword(self):
        """Test no booking intent without booking keyword."""
        assert extract_booking_intent("am 20.01.2025 um 14:00", "") is False


class TestCustomerDataFlow:
    """Integration tests for customer data management during booking."""

    def test_new_customer_flow(self, temp_customers_file):
        """Test new customer is created with default data."""
        service = CustomerService(memory_file=temp_customers_file)

        customer = service.get("491234567890")

        assert customer["name"] == "du"
        assert customer["status"] == "neuer Interessent"
        assert customer["profil"]["magicline_customer_id"] is None

    def test_customer_profile_update_flow(self, temp_customers_file):
        """Test profile updates persist correctly."""
        service = CustomerService(memory_file=temp_customers_file)
        service.get("491234567890")

        # Update profile with name
        service.update_profil("491234567890", {
            "vorname": "Max",
            "nachname": "Mustermann",
            "email": "max@test.de",
        })

        # Verify updates
        customer = service.get("491234567890")
        assert customer["profil"]["vorname"] == "Max"
        assert customer["profil"]["nachname"] == "Mustermann"
        assert customer["profil"]["email"] == "max@test.de"
        assert customer["name"] == "Max"  # Name updated from vorname

    def test_customer_status_progression(self, temp_customers_file):
        """Test customer status progression through booking flow."""
        service = CustomerService(memory_file=temp_customers_file)

        # New customer
        customer = service.get("491234567890")
        assert customer["status"] == "neuer Interessent"

        # After name is known
        service.update_status("491234567890", "Name bekannt")
        customer = service.get("491234567890")
        assert customer["status"] == "Name bekannt"

        # After booking
        service.update_status("491234567890", "Probetraining gebucht")
        customer = service.get("491234567890")
        assert customer["status"] == "Probetraining gebucht"


class TestRegisteredCustomerBooking:
    """Integration tests for registered customer booking flow."""

    @responses.activate
    def test_registered_customer_successful_booking(self, temp_customers_file):
        """Test complete booking flow for registered customer."""
        base_url = "https://mock-api.magicline.com/v1"

        # Setup customer with MagicLine ID
        customer_service = CustomerService(memory_file=temp_customers_file)
        customer_service.get("491234567890")
        customer_service.update_profil("491234567890", {
            "magicline_customer_id": 12345,
            "vorname": "Anna",
            "nachname": "Schmidt",
            "email": "anna@test.de",
        })

        # Mock API responses
        responses.add(
            responses.POST,
            f"{base_url}/appointments/bookable/validate",
            json={"validationStatus": "AVAILABLE"},
            status=200,
        )
        responses.add(
            responses.POST,
            f"{base_url}/appointments/booking/book",
            json={"success": True, "bookingId": 123456},
            status=200,
        )

        # Execute booking
        booking_service = BookingService()
        success, message, booking_id = booking_service.try_book(
            customer_id=12345,
            start_datetime="2025-01-20T14:00:00+01:00",
        )

        assert success is True
        assert booking_id == 123456

    @responses.activate
    def test_registered_customer_slot_unavailable(self, temp_customers_file):
        """Test booking fails when slot not available."""
        base_url = "https://mock-api.magicline.com/v1"

        responses.add(
            responses.POST,
            f"{base_url}/appointments/bookable/validate",
            json={"validationStatus": "NOT_AVAILABLE"},
            status=200,
        )

        booking_service = BookingService()
        success, message, booking_id = booking_service.try_book(
            customer_id=12345,
            start_datetime="2025-01-20T14:00:00+01:00",
        )

        assert success is False
        assert booking_id is None


class TestTrialOfferBooking:
    """Integration tests for trial offer booking flow (new leads)."""

    @responses.activate
    def test_trial_offer_full_flow(self, temp_customers_file):
        """Test complete trial offer flow for new lead."""
        base_url = "https://mock-api.magicline.com/v1"

        # Setup new lead customer
        customer_service = CustomerService(memory_file=temp_customers_file)
        customer_service.get("491234567890")
        customer_service.update_profil("491234567890", {
            "vorname": "Max",
            "nachname": "Mustermann",
            "email": "max@test.de",
        })

        # Mock all 4 API calls
        responses.add(
            responses.POST,
            f"{base_url}/trial-offers/lead/validate",
            json={"success": True},
            status=200,
        )
        responses.add(
            responses.POST,
            f"{base_url}/trial-offers/lead/create",
            json={"success": True, "leadCustomerId": 67890},
            status=200,
        )
        responses.add(
            responses.POST,
            f"{base_url}/appointments/bookable/validate",
            json={"success": True, "validationStatus": "AVAILABLE"},
            status=200,
        )
        responses.add(
            responses.POST,
            f"{base_url}/appointments/booking/book",
            json={"success": True, "bookingId": 999999},
            status=200,
        )

        # Execute booking
        booking_service = BookingService()
        success, message, booking_id = booking_service.try_book_trial_offer(
            first_name="Max",
            last_name="Mustermann",
            email="max@test.de",
            start_datetime="2025-01-20T14:00:00+01:00",
        )

        assert success is True
        assert booking_id == 999999

    @responses.activate
    def test_trial_offer_lead_validation_fails(self, temp_customers_file):
        """Test trial offer fails when lead validation fails."""
        base_url = "https://mock-api.magicline.com/v1"

        responses.add(
            responses.POST,
            f"{base_url}/trial-offers/lead/validate",
            json={"success": False, "error": "Invalid email"},
            status=200,
        )

        booking_service = BookingService()
        success, message, booking_id = booking_service.try_book_trial_offer(
            first_name="Max",
            last_name="Mustermann",
            email="invalid",
            start_datetime="2025-01-20T14:00:00+01:00",
        )

        assert success is False
        assert "validiert" in message.lower() or "daten" in message.lower()

    @responses.activate
    def test_trial_offer_slot_unavailable(self, temp_customers_file):
        """Test trial offer fails when slot not available."""
        base_url = "https://mock-api.magicline.com/v1"

        responses.add(
            responses.POST,
            f"{base_url}/trial-offers/lead/validate",
            json={"success": True},
            status=200,
        )
        responses.add(
            responses.POST,
            f"{base_url}/trial-offers/lead/create",
            json={"success": True, "leadCustomerId": 67890},
            status=200,
        )
        responses.add(
            responses.POST,
            f"{base_url}/appointments/bookable/validate",
            json={"success": True, "validationStatus": "NOT_AVAILABLE"},
            status=200,
        )

        booking_service = BookingService()
        success, message, booking_id = booking_service.try_book_trial_offer(
            first_name="Max",
            last_name="Mustermann",
            email="max@test.de",
            start_datetime="2025-01-20T14:00:00+01:00",
        )

        assert success is False
        assert "nicht" in message.lower()


class TestExtractionIntegration:
    """Integration tests for data extraction with booking."""

    def test_extraction_builds_datetime(self):
        """Test extraction service builds ISO datetime correctly."""
        mock_llm = MagicMock()
        mock_llm.generate.return_value = '{"vorname": "Max", "nachname": "Mustermann", "email": "max@test.de", "datum": "2025-01-20", "uhrzeit": "14:00"}'

        service = ExtractionService(mock_llm)
        result = service.extract_customer_data("Probetraining am 20.01. um 14 Uhr")

        datetime_iso = service.build_datetime_iso(result["datum"], result["uhrzeit"])
        assert datetime_iso == "2025-01-20T14:00:00+01:00"

    def test_extraction_missing_time_no_datetime(self):
        """Test no datetime built when time is missing."""
        mock_llm = MagicMock()
        mock_llm.generate.return_value = '{"vorname": null, "nachname": null, "email": null, "datum": "2025-01-20", "uhrzeit": null}'

        service = ExtractionService(mock_llm)
        result = service.extract_customer_data("Probetraining am 20.01.")

        datetime_iso = service.build_datetime_iso(result["datum"], result["uhrzeit"])
        assert datetime_iso is None


class TestEndToEndScenarios:
    """End-to-end scenario tests."""

    @responses.activate
    def test_new_lead_complete_journey(self, temp_customers_file):
        """Test complete journey from new lead to booked appointment."""
        base_url = "https://mock-api.magicline.com/v1"

        # Mock LLM
        mock_llm = MagicMock()

        # Step 1: New customer arrives
        customer_service = CustomerService(memory_file=temp_customers_file)
        customer = customer_service.get("491234567890")
        assert customer["status"] == "neuer Interessent"

        # Step 2: Customer provides name
        mock_llm.generate.return_value = '{"vorname": "Max", "nachname": "Mustermann", "email": null, "datum": null, "uhrzeit": null}'
        extraction_service = ExtractionService(mock_llm)
        extracted = extraction_service.extract_customer_data("Ich bin Max Mustermann")

        customer_service.update_profil("491234567890", {
            "vorname": extracted["vorname"],
            "nachname": extracted["nachname"],
        })
        customer_service.update_status("491234567890", "Name bekannt")

        customer = customer_service.get("491234567890")
        assert customer["status"] == "Name bekannt"
        assert customer["name"] == "Max"

        # Step 3: Customer provides email and booking request
        mock_llm.generate.return_value = '{"vorname": null, "nachname": null, "email": "max@test.de", "datum": "2025-01-20", "uhrzeit": "14:00"}'
        extracted = extraction_service.extract_customer_data("Probetraining am 20.01. um 14 Uhr, email max@test.de")

        customer_service.update_profil("491234567890", {"email": extracted["email"]})

        # Step 4: Execute trial offer booking
        responses.add(responses.POST, f"{base_url}/trial-offers/lead/validate", json={"success": True}, status=200)
        responses.add(responses.POST, f"{base_url}/trial-offers/lead/create", json={"success": True, "leadCustomerId": 67890}, status=200)
        responses.add(responses.POST, f"{base_url}/appointments/bookable/validate", json={"success": True, "validationStatus": "AVAILABLE"}, status=200)
        responses.add(responses.POST, f"{base_url}/appointments/booking/book", json={"success": True, "bookingId": 111222}, status=200)

        customer = customer_service.get("491234567890")
        booking_service = BookingService()

        datetime_iso = extraction_service.build_datetime_iso(extracted["datum"], extracted["uhrzeit"])
        success, message, booking_id = booking_service.try_book_trial_offer(
            first_name=customer["profil"]["vorname"],
            last_name=customer["profil"]["nachname"],
            email=customer["profil"]["email"],
            start_datetime=datetime_iso,
        )

        assert success is True
        assert booking_id == 111222

        # Step 5: Update status after successful booking
        customer_service.update_status("491234567890", "Probetraining gebucht")
        customer = customer_service.get("491234567890")
        assert customer["status"] == "Probetraining gebucht"
