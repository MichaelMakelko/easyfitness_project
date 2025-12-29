"""Unit tests for BookingService with mocked API calls."""

import pytest
import responses
from requests.exceptions import RequestException

from services.booking_service import BookingService
from tests.fixtures.magicline_responses import (
    BOOKING_SUCCESS,
    BOOKING_FAILED,
    LEAD_CREATION_SUCCESS,
    LEAD_VALIDATION_SUCCESS,
    VALIDATION_AVAILABLE,
    VALIDATION_NOT_AVAILABLE,
)


@pytest.fixture
def booking_service() -> BookingService:
    """Create BookingService instance for testing."""
    return BookingService()


@pytest.fixture
def base_url() -> str:
    """Get MagicLine base URL from environment."""
    return "https://mock-api.magicline.com/v1"


class TestValidateSlot:
    """Tests for validate_slot method."""

    @responses.activate
    def test_validate_slot_available(self, booking_service, base_url):
        """Test slot validation when slot is available."""
        responses.add(
            responses.POST,
            f"{base_url}/appointments/bookable/validate",
            json=VALIDATION_AVAILABLE,
            status=200,
        )

        result = booking_service.validate_slot(
            customer_id=12345,
            start_datetime="2025-01-20T14:00:00+01:00",
        )

        assert result["validationStatus"] == "AVAILABLE"

    @responses.activate
    def test_validate_slot_not_available(self, booking_service, base_url):
        """Test slot validation when slot is not available."""
        responses.add(
            responses.POST,
            f"{base_url}/appointments/bookable/validate",
            json=VALIDATION_NOT_AVAILABLE,
            status=200,
        )

        result = booking_service.validate_slot(
            customer_id=12345,
            start_datetime="2025-01-20T14:00:00+01:00",
        )

        assert result["validationStatus"] == "NOT_AVAILABLE"

    @responses.activate
    def test_validate_slot_request_error(self, booking_service, base_url):
        """Test slot validation handles request errors."""
        responses.add(
            responses.POST,
            f"{base_url}/appointments/bookable/validate",
            body=RequestException("Connection error"),
        )

        result = booking_service.validate_slot(
            customer_id=12345,
            start_datetime="2025-01-20T14:00:00+01:00",
        )

        assert result["validationStatus"] == "ERROR"
        assert "error" in result

    @responses.activate
    def test_validate_slot_sends_correct_payload(self, booking_service, base_url):
        """Test correct payload is sent to API."""
        responses.add(
            responses.POST,
            f"{base_url}/appointments/bookable/validate",
            json=VALIDATION_AVAILABLE,
            status=200,
        )

        booking_service.validate_slot(
            customer_id=12345,
            start_datetime="2025-01-20T14:00:00+01:00",
            duration_minutes=30,
        )

        request_body = responses.calls[0].request.body
        assert b'"customerId": 12345' in request_body
        assert b'"startDateTime": "2025-01-20T14:00:00+01:00"' in request_body
        assert b'"endDateTime": "2025-01-20T14:30:00+01:00"' in request_body


class TestBookAppointment:
    """Tests for book_appointment method."""

    @responses.activate
    def test_book_appointment_success(self, booking_service, base_url):
        """Test successful appointment booking."""
        responses.add(
            responses.POST,
            f"{base_url}/appointments/booking/book",
            json=BOOKING_SUCCESS,
            status=200,
        )

        result = booking_service.book_appointment(
            customer_id=12345,
            start_datetime="2025-01-20T14:00:00+01:00",
        )

        assert result["success"] is True
        assert result["bookingId"] == 1234567890

    @responses.activate
    def test_book_appointment_failure(self, booking_service, base_url):
        """Test failed appointment booking."""
        responses.add(
            responses.POST,
            f"{base_url}/appointments/booking/book",
            json=BOOKING_FAILED,
            status=400,
        )

        result = booking_service.book_appointment(
            customer_id=12345,
            start_datetime="2025-01-20T14:00:00+01:00",
        )

        assert result["success"] is False

    @responses.activate
    def test_book_appointment_request_error(self, booking_service, base_url):
        """Test booking handles request errors."""
        responses.add(
            responses.POST,
            f"{base_url}/appointments/booking/book",
            body=RequestException("Connection error"),
        )

        result = booking_service.book_appointment(
            customer_id=12345,
            start_datetime="2025-01-20T14:00:00+01:00",
        )

        assert result["success"] is False
        assert "error" in result


class TestTryBook:
    """Tests for try_book method (validate + book)."""

    @responses.activate
    def test_try_book_success(self, booking_service, base_url):
        """Test successful validate and book flow."""
        # Mock validation
        responses.add(
            responses.POST,
            f"{base_url}/appointments/bookable/validate",
            json=VALIDATION_AVAILABLE,
            status=200,
        )
        # Mock booking
        responses.add(
            responses.POST,
            f"{base_url}/appointments/booking/book",
            json=BOOKING_SUCCESS,
            status=200,
        )

        success, message, booking_id = booking_service.try_book(
            customer_id=12345,
            start_datetime="2025-01-20T14:00:00+01:00",
        )

        assert success is True
        assert "gebucht" in message.lower() or "termin" in message.lower()
        assert booking_id == 1234567890

    @responses.activate
    def test_try_book_slot_not_available(self, booking_service, base_url):
        """Test try_book when slot is not available."""
        responses.add(
            responses.POST,
            f"{base_url}/appointments/bookable/validate",
            json=VALIDATION_NOT_AVAILABLE,
            status=200,
        )

        success, message, booking_id = booking_service.try_book(
            customer_id=12345,
            start_datetime="2025-01-20T14:00:00+01:00",
        )

        assert success is False
        assert "nicht" in message.lower()
        assert booking_id is None

    @responses.activate
    def test_try_book_booking_fails_after_validation(self, booking_service, base_url):
        """Test try_book when booking fails after successful validation."""
        responses.add(
            responses.POST,
            f"{base_url}/appointments/bookable/validate",
            json=VALIDATION_AVAILABLE,
            status=200,
        )
        responses.add(
            responses.POST,
            f"{base_url}/appointments/booking/book",
            json=BOOKING_FAILED,
            status=400,
        )

        success, message, booking_id = booking_service.try_book(
            customer_id=12345,
            start_datetime="2025-01-20T14:00:00+01:00",
        )

        assert success is False
        assert booking_id is None


class TestTrialOfferFlow:
    """Tests for trial offer booking flow (4 steps)."""

    @responses.activate
    def test_validate_lead_success(self, booking_service, base_url):
        """Test lead validation success."""
        responses.add(
            responses.POST,
            f"{base_url}/trial-offers/lead/validate",
            json=LEAD_VALIDATION_SUCCESS,
            status=200,
        )

        result = booking_service.validate_lead(
            first_name="Max",
            last_name="Mustermann",
            email="max@test.de",
        )

        assert result["success"] is True

    @responses.activate
    def test_validate_lead_failure(self, booking_service, base_url):
        """Test lead validation failure."""
        responses.add(
            responses.POST,
            f"{base_url}/trial-offers/lead/validate",
            json={"valid": False, "error": "Invalid email"},
            status=400,
        )

        result = booking_service.validate_lead(
            first_name="Max",
            last_name="Mustermann",
            email="invalid-email",
        )

        assert result["success"] is False

    @responses.activate
    def test_create_lead_success(self, booking_service, base_url):
        """Test lead creation success."""
        responses.add(
            responses.POST,
            f"{base_url}/trial-offers/lead/create",
            json=LEAD_CREATION_SUCCESS,
            status=200,
        )

        result = booking_service.create_lead(
            first_name="Max",
            last_name="Mustermann",
            email="max@test.de",
        )

        assert result["success"] is True
        assert result["leadCustomerId"] == 67890

    @responses.activate
    def test_create_lead_failure(self, booking_service, base_url):
        """Test lead creation failure."""
        responses.add(
            responses.POST,
            f"{base_url}/trial-offers/lead/create",
            json={"error": "Duplicate email"},
            status=400,
        )

        result = booking_service.create_lead(
            first_name="Max",
            last_name="Mustermann",
            email="max@test.de",
        )

        assert result["success"] is False

    @responses.activate
    def test_try_book_trial_offer_full_flow(self, booking_service, base_url):
        """Test complete trial offer booking flow."""
        # Step 1: Validate lead
        responses.add(
            responses.POST,
            f"{base_url}/trial-offers/lead/validate",
            json={"success": True},
            status=200,
        )
        # Step 2: Create lead
        responses.add(
            responses.POST,
            f"{base_url}/trial-offers/lead/create",
            json={"success": True, "leadCustomerId": 67890},
            status=200,
        )
        # Step 3: Validate appointment
        responses.add(
            responses.POST,
            f"{base_url}/appointments/bookable/validate",
            json={"success": True, "validationStatus": "AVAILABLE"},
            status=200,
        )
        # Step 4: Book appointment
        responses.add(
            responses.POST,
            f"{base_url}/appointments/booking/book",
            json={"success": True, "bookingId": 1234567890},
            status=200,
        )

        success, message, booking_id = booking_service.try_book_trial_offer(
            first_name="Max",
            last_name="Mustermann",
            email="max@test.de",
            start_datetime="2025-01-20T14:00:00+01:00",
        )

        assert success is True
        assert booking_id == 1234567890

    @responses.activate
    def test_try_book_trial_offer_lead_validation_fails(self, booking_service, base_url):
        """Test trial offer when lead validation fails."""
        responses.add(
            responses.POST,
            f"{base_url}/trial-offers/lead/validate",
            json={"success": False, "error": "Invalid email"},
            status=200,
        )

        success, message, booking_id = booking_service.try_book_trial_offer(
            first_name="Max",
            last_name="Mustermann",
            email="invalid-email",
            start_datetime="2025-01-20T14:00:00+01:00",
        )

        assert success is False
        assert booking_id is None

    @responses.activate
    def test_try_book_trial_offer_lead_creation_fails(self, booking_service, base_url):
        """Test trial offer when lead creation fails."""
        responses.add(
            responses.POST,
            f"{base_url}/trial-offers/lead/validate",
            json={"success": True},
            status=200,
        )
        responses.add(
            responses.POST,
            f"{base_url}/trial-offers/lead/create",
            json={"success": False, "error": "Duplicate"},
            status=200,
        )

        success, message, booking_id = booking_service.try_book_trial_offer(
            first_name="Max",
            last_name="Mustermann",
            email="max@test.de",
            start_datetime="2025-01-20T14:00:00+01:00",
        )

        assert success is False
        assert booking_id is None

    @responses.activate
    def test_try_book_trial_offer_slot_not_available(self, booking_service, base_url):
        """Test trial offer when slot is not available."""
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

        success, message, booking_id = booking_service.try_book_trial_offer(
            first_name="Max",
            last_name="Mustermann",
            email="max@test.de",
            start_datetime="2025-01-20T14:00:00+01:00",
        )

        assert success is False
        assert "nicht" in message.lower()


class TestCalculateEndTime:
    """Tests for _calculate_end_time helper method."""

    def test_calculate_end_time_30_minutes(self, booking_service):
        """Test end time calculation for 30 minute duration."""
        result = booking_service._calculate_end_time(
            "2025-01-20T14:00:00+01:00", 30
        )
        assert result == "2025-01-20T14:30:00+01:00"

    def test_calculate_end_time_60_minutes(self, booking_service):
        """Test end time calculation for 60 minute duration."""
        result = booking_service._calculate_end_time(
            "2025-01-20T14:00:00+01:00", 60
        )
        assert result == "2025-01-20T15:00:00+01:00"

    def test_calculate_end_time_crosses_hour(self, booking_service):
        """Test end time calculation that crosses hour boundary."""
        result = booking_service._calculate_end_time(
            "2025-01-20T14:45:00+01:00", 30
        )
        assert result == "2025-01-20T15:15:00+01:00"

    def test_calculate_end_time_preserves_timezone(self, booking_service):
        """Test that timezone is preserved in end time."""
        result = booking_service._calculate_end_time(
            "2025-01-20T14:00:00+02:00", 30
        )
        assert result == "2025-01-20T14:30:00+02:00"

    def test_calculate_end_time_without_timezone(self, booking_service):
        """Test end time calculation without timezone (uses default +01:00)."""
        result = booking_service._calculate_end_time(
            "2025-01-20T14:00:00", 30
        )
        assert result == "2025-01-20T14:30:00+01:00"

    def test_calculate_end_time_invalid_format_fallback(self, booking_service):
        """Test fallback for invalid datetime format."""
        result = booking_service._calculate_end_time(
            "invalid-datetime", 30
        )
        assert result == "invalid-datetime"  # Returns original on parse failure
