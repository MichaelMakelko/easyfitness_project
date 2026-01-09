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
        """Test complete trial offer booking flow (with pre-check fallback)."""
        # Pre-check fails → fallback to old flow
        responses.add(
            responses.GET,
            f"{base_url}/trial-offers/appointments/{booking_service.bookable_id}/slots",
            json={"error": "Server error"},
            status=500,
        )
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
        # Pre-check fails → fallback to old flow
        responses.add(
            responses.GET,
            f"{base_url}/trial-offers/appointments/{booking_service.bookable_id}/slots",
            json={"error": "Server error"},
            status=500,
        )
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
        # Pre-check fails → fallback to old flow
        responses.add(
            responses.GET,
            f"{base_url}/trial-offers/appointments/{booking_service.bookable_id}/slots",
            json={"error": "Server error"},
            status=500,
        )
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
        """Test trial offer when slot is not available (via fallback)."""
        # Pre-check fails → fallback to old flow
        responses.add(
            responses.GET,
            f"{base_url}/trial-offers/appointments/{booking_service.bookable_id}/slots",
            json={"error": "Server error"},
            status=500,
        )
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


# ==================== SLOT AVAILABILITY TESTS ====================

class TestGetAvailableSlots:
    """Tests for get_available_slots method."""

    @responses.activate
    def test_get_available_slots_success_list_response(self, booking_service, base_url):
        """Test successful slot retrieval when API returns a list."""
        from tests.fixtures.magicline_responses import SLOTS_AVAILABLE

        responses.add(
            responses.GET,
            f"{base_url}/trial-offers/appointments/{booking_service.bookable_id}/slots",
            json=SLOTS_AVAILABLE,
            status=200,
        )

        result = booking_service.get_available_slots("2025-01-20")

        assert result["success"] is True
        assert len(result["slots"]) == 6
        assert result["slots"][0]["startDateTime"] == "2025-01-20T09:00:00+01:00"

    @responses.activate
    def test_get_available_slots_success_dict_response(self, booking_service, base_url):
        """Test successful slot retrieval when API returns a dict with slots key."""
        from tests.fixtures.magicline_responses import SLOTS_AVAILABLE

        responses.add(
            responses.GET,
            f"{base_url}/trial-offers/appointments/{booking_service.bookable_id}/slots",
            json={"slots": SLOTS_AVAILABLE},
            status=200,
        )

        result = booking_service.get_available_slots("2025-01-20")

        assert result["success"] is True
        assert len(result["slots"]) == 6

    @responses.activate
    def test_get_available_slots_empty(self, booking_service, base_url):
        """Test slot retrieval when no slots available."""
        responses.add(
            responses.GET,
            f"{base_url}/trial-offers/appointments/{booking_service.bookable_id}/slots",
            json=[],
            status=200,
        )

        result = booking_service.get_available_slots("2025-01-20")

        assert result["success"] is True
        assert result["slots"] == []

    @responses.activate
    def test_get_available_slots_api_error(self, booking_service, base_url):
        """Test slot retrieval handles API errors."""
        responses.add(
            responses.GET,
            f"{base_url}/trial-offers/appointments/{booking_service.bookable_id}/slots",
            json={"error": "Unauthorized"},
            status=401,
        )

        result = booking_service.get_available_slots("2025-01-20")

        assert result["success"] is False
        assert result["slots"] == []
        assert "error" in result

    @responses.activate
    def test_get_available_slots_network_error(self, booking_service, base_url):
        """Test slot retrieval handles network errors."""
        responses.add(
            responses.GET,
            f"{base_url}/trial-offers/appointments/{booking_service.bookable_id}/slots",
            body=RequestException("Connection error"),
        )

        result = booking_service.get_available_slots("2025-01-20")

        assert result["success"] is False
        assert result["is_network_error"] is True


class TestCheckSlotAvailability:
    """Tests for check_slot_availability method."""

    @responses.activate
    def test_check_slot_available(self, booking_service, base_url):
        """Test check when slot is available."""
        from tests.fixtures.magicline_responses import SLOTS_AVAILABLE

        responses.add(
            responses.GET,
            f"{base_url}/trial-offers/appointments/{booking_service.bookable_id}/slots",
            json=SLOTS_AVAILABLE,
            status=200,
        )

        result = booking_service.check_slot_availability("2025-01-20T14:00:00+01:00")

        assert result["available"] is True
        assert result["alternatives"] == []
        assert result["api_error"] is False

    @responses.activate
    def test_check_slot_not_available_with_alternatives(self, booking_service, base_url):
        """Test check when slot is not available but alternatives exist."""
        from tests.fixtures.magicline_responses import SLOTS_AVAILABLE

        responses.add(
            responses.GET,
            f"{base_url}/trial-offers/appointments/{booking_service.bookable_id}/slots",
            json=SLOTS_AVAILABLE,
            status=200,
        )

        # Request 12:00 which is not in SLOTS_AVAILABLE
        result = booking_service.check_slot_availability("2025-01-20T12:00:00+01:00")

        assert result["available"] is False
        assert len(result["alternatives"]) > 0
        # Should suggest closest times (11:00 and 14:00 are closest to 12:00)
        assert "11:00" in result["alternatives"] or "14:00" in result["alternatives"]
        assert result["api_error"] is False

    @responses.activate
    def test_check_slot_no_slots_available(self, booking_service, base_url):
        """Test check when no slots available for the day."""
        responses.add(
            responses.GET,
            f"{base_url}/trial-offers/appointments/{booking_service.bookable_id}/slots",
            json=[],
            status=200,
        )

        result = booking_service.check_slot_availability("2025-01-20T14:00:00+01:00")

        assert result["available"] is False
        assert result["alternatives"] == []
        assert result["api_error"] is False

    @responses.activate
    def test_check_slot_api_error_signals_fallback(self, booking_service, base_url):
        """Test check returns api_error=True on API failure for fallback."""
        responses.add(
            responses.GET,
            f"{base_url}/trial-offers/appointments/{booking_service.bookable_id}/slots",
            json={"error": "Server error"},
            status=500,
        )

        result = booking_service.check_slot_availability("2025-01-20T14:00:00+01:00")

        assert result["available"] is False
        assert result["api_error"] is True

    def test_check_slot_invalid_datetime(self, booking_service):
        """Test check handles invalid datetime format."""
        result = booking_service.check_slot_availability("")

        assert result["available"] is False
        assert result["api_error"] is True


class TestSlotHelperMethods:
    """Tests for slot-related helper methods."""

    def test_extract_date_from_datetime(self, booking_service):
        """Test date extraction from ISO datetime."""
        result = booking_service._extract_date_from_datetime("2025-01-20T14:00:00+01:00")
        assert result == "2025-01-20"

    def test_extract_date_from_datetime_none(self, booking_service):
        """Test date extraction handles None."""
        result = booking_service._extract_date_from_datetime(None)
        assert result is None

    def test_extract_date_from_datetime_empty(self, booking_service):
        """Test date extraction handles empty string."""
        result = booking_service._extract_date_from_datetime("")
        assert result is None

    def test_extract_time_from_datetime(self, booking_service):
        """Test time extraction from ISO datetime."""
        result = booking_service._extract_time_from_datetime("2025-01-20T14:30:00+01:00")
        assert result == "14:30"

    def test_extract_time_from_datetime_none(self, booking_service):
        """Test time extraction handles None."""
        result = booking_service._extract_time_from_datetime(None)
        assert result is None

    def test_extract_time_from_datetime_no_t_separator(self, booking_service):
        """Test time extraction handles missing T separator."""
        result = booking_service._extract_time_from_datetime("2025-01-20")
        assert result is None

    def test_is_slot_in_list_found(self, booking_service):
        """Test slot found in list."""
        slots = [
            {"startDateTime": "2025-01-20T14:00:00+01:00"},
            {"startDateTime": "2025-01-20T15:00:00+01:00"},
        ]
        result = booking_service._is_slot_in_list("2025-01-20T14:00:00+01:00", slots)
        assert result is True

    def test_is_slot_in_list_not_found(self, booking_service):
        """Test slot not in list."""
        slots = [
            {"startDateTime": "2025-01-20T14:00:00+01:00"},
            {"startDateTime": "2025-01-20T15:00:00+01:00"},
        ]
        result = booking_service._is_slot_in_list("2025-01-20T12:00:00+01:00", slots)
        assert result is False

    def test_is_slot_in_list_empty(self, booking_service):
        """Test slot check with empty list."""
        result = booking_service._is_slot_in_list("2025-01-20T14:00:00+01:00", [])
        assert result is False

    def test_is_slot_in_list_different_field_names(self, booking_service):
        """Test slot check with alternative field names."""
        slots = [{"start": "2025-01-20T14:00:00+01:00"}]
        result = booking_service._is_slot_in_list("2025-01-20T14:00:00+01:00", slots)
        assert result is True

    def test_get_alternative_slots_sorted_by_distance(self, booking_service):
        """Test alternatives are sorted by distance from target."""
        slots = [
            {"startDateTime": "2025-01-20T09:00:00+01:00"},
            {"startDateTime": "2025-01-20T16:00:00+01:00"},
            {"startDateTime": "2025-01-20T11:00:00+01:00"},
        ]
        # Target is 12:00, so closest should be 11:00 (1h), then 09:00 (3h), then 16:00 (4h)
        result = booking_service._get_alternative_slots(
            "2025-01-20T12:00:00+01:00", slots, max_alternatives=3
        )
        assert result == ["11:00", "09:00", "16:00"]

    def test_get_alternative_slots_max_limit(self, booking_service):
        """Test alternatives respects max_alternatives limit."""
        slots = [
            {"startDateTime": "2025-01-20T09:00:00+01:00"},
            {"startDateTime": "2025-01-20T10:00:00+01:00"},
            {"startDateTime": "2025-01-20T11:00:00+01:00"},
            {"startDateTime": "2025-01-20T14:00:00+01:00"},
        ]
        result = booking_service._get_alternative_slots(
            "2025-01-20T12:00:00+01:00", slots, max_alternatives=2
        )
        assert len(result) == 2

    def test_time_to_minutes(self, booking_service):
        """Test time to minutes conversion."""
        assert booking_service._time_to_minutes("14:30") == 14 * 60 + 30
        assert booking_service._time_to_minutes("00:00") == 0
        assert booking_service._time_to_minutes("23:59") == 23 * 60 + 59

    def test_time_to_minutes_invalid(self, booking_service):
        """Test time to minutes handles invalid input."""
        assert booking_service._time_to_minutes(None) is None
        assert booking_service._time_to_minutes("") is None
        assert booking_service._time_to_minutes("invalid") is None


class TestTrialOfferWithPreCheck:
    """Tests for try_book_trial_offer with slot pre-check."""

    @responses.activate
    def test_try_book_trial_offer_with_precheck_success(self, booking_service, base_url):
        """Test full trial offer flow with successful pre-check."""
        from tests.fixtures.magicline_responses import SLOTS_AVAILABLE

        # Step 0: Pre-check slots
        responses.add(
            responses.GET,
            f"{base_url}/trial-offers/appointments/{booking_service.bookable_id}/slots",
            json=SLOTS_AVAILABLE,
            status=200,
        )
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
        # Verify 5 API calls were made
        assert len(responses.calls) == 5

    @responses.activate
    def test_try_book_trial_offer_slot_not_available_early_return(self, booking_service, base_url):
        """Test trial offer returns early when slot not available (no lead created)."""
        # Only slots at 09:00, 10:00, 11:00 - NOT 14:00
        limited_slots = [
            {"startDateTime": "2025-01-20T09:00:00+01:00"},
            {"startDateTime": "2025-01-20T10:00:00+01:00"},
            {"startDateTime": "2025-01-20T11:00:00+01:00"},
        ]

        responses.add(
            responses.GET,
            f"{base_url}/trial-offers/appointments/{booking_service.bookable_id}/slots",
            json=limited_slots,
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
        # Should contain alternatives in message
        assert "11:00" in message or "belegt" in message.lower()
        # CRITICAL: Only 1 API call (GET slots) - NO lead created!
        assert len(responses.calls) == 1

    @responses.activate
    def test_try_book_trial_offer_precheck_api_error_fallback(self, booking_service, base_url):
        """Test trial offer falls back to old flow on pre-check API error."""
        # Pre-check fails with server error
        responses.add(
            responses.GET,
            f"{base_url}/trial-offers/appointments/{booking_service.bookable_id}/slots",
            json={"error": "Server error"},
            status=500,
        )
        # Old flow continues...
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
            json={"success": True, "bookingId": 999},
            status=200,
        )

        success, message, booking_id = booking_service.try_book_trial_offer(
            first_name="Max",
            last_name="Mustermann",
            email="max@test.de",
            start_datetime="2025-01-20T14:00:00+01:00",
        )

        # Should succeed via fallback
        assert success is True
        assert booking_id == 999
        # 5 API calls: failed pre-check + 4 old flow steps
        assert len(responses.calls) == 5

    @responses.activate
    def test_try_book_trial_offer_no_slots_no_alternatives(self, booking_service, base_url):
        """Test trial offer when no slots available at all."""
        responses.add(
            responses.GET,
            f"{base_url}/trial-offers/appointments/{booking_service.bookable_id}/slots",
            json=[],
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
        # Should get standard unavailable message (no alternatives)
        assert "nicht" in message.lower() or "unavailable" in message.lower()
        # Only 1 API call - no lead created
        assert len(responses.calls) == 1
