"""MagicLine API response mocks for testing."""

from typing import Any


# ==================== Validation Responses ====================

VALIDATION_AVAILABLE: dict[str, Any] = {
    "validationStatus": "AVAILABLE",
    "slotDetails": {
        "startDateTime": "2025-01-20T14:00:00+01:00",
        "endDateTime": "2025-01-20T14:30:00+01:00",
    },
}

VALIDATION_NOT_AVAILABLE: dict[str, Any] = {
    "validationStatus": "NOT_AVAILABLE",
    "reason": "Slot already booked",
}

VALIDATION_ERROR: dict[str, Any] = {
    "validationStatus": "ERROR",
    "error": "Invalid request",
}


# ==================== Booking Responses ====================

BOOKING_SUCCESS: dict[str, Any] = {
    "bookingId": 1234567890,
    "status": "CONFIRMED",
    "startDateTime": "2025-01-20T14:00:00+01:00",
    "endDateTime": "2025-01-20T14:30:00+01:00",
}

BOOKING_FAILED: dict[str, Any] = {
    "error": "Booking failed",
    "reason": "Slot no longer available",
}


# ==================== Lead Responses ====================

LEAD_VALIDATION_SUCCESS: dict[str, Any] = {
    "valid": True,
    "message": "Lead data is valid",
}

LEAD_VALIDATION_FAILED: dict[str, Any] = {
    "valid": False,
    "message": "Invalid email format",
}

LEAD_CREATION_SUCCESS: dict[str, Any] = {
    "leadCustomerId": 67890,
    "status": "CREATED",
}

LEAD_CREATION_FAILED: dict[str, Any] = {
    "error": "Lead creation failed",
    "reason": "Duplicate email",
}


def create_booking_response(
    success: bool = True,
    booking_id: int = 1234567890,
    error_message: str | None = None,
) -> dict[str, Any]:
    """Create a configurable booking response."""
    if success:
        return {
            "bookingId": booking_id,
            "status": "CONFIRMED",
        }
    return {
        "error": error_message or "Booking failed",
    }


def create_validation_response(
    available: bool = True,
    status: str | None = None,
) -> dict[str, Any]:
    """Create a configurable validation response."""
    if available:
        return {"validationStatus": status or "AVAILABLE"}
    return {"validationStatus": status or "NOT_AVAILABLE"}


def create_lead_response(
    success: bool = True,
    lead_customer_id: int = 67890,
    error_message: str | None = None,
) -> dict[str, Any]:
    """Create a configurable lead creation response."""
    if success:
        return {
            "success": True,
            "leadCustomerId": lead_customer_id,
        }
    return {
        "success": False,
        "error": error_message or "Lead creation failed",
    }
