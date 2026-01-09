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


# ==================== Slot Availability Responses ====================

SLOTS_AVAILABLE: list[dict[str, Any]] = [
    {
        "startDateTime": "2025-01-20T09:00:00+01:00",
        "endDateTime": "2025-01-20T09:30:00+01:00",
    },
    {
        "startDateTime": "2025-01-20T10:00:00+01:00",
        "endDateTime": "2025-01-20T10:30:00+01:00",
    },
    {
        "startDateTime": "2025-01-20T11:00:00+01:00",
        "endDateTime": "2025-01-20T11:30:00+01:00",
    },
    {
        "startDateTime": "2025-01-20T14:00:00+01:00",
        "endDateTime": "2025-01-20T14:30:00+01:00",
    },
    {
        "startDateTime": "2025-01-20T15:00:00+01:00",
        "endDateTime": "2025-01-20T15:30:00+01:00",
    },
    {
        "startDateTime": "2025-01-20T16:00:00+01:00",
        "endDateTime": "2025-01-20T16:30:00+01:00",
    },
]

SLOTS_EMPTY: list[dict[str, Any]] = []


def create_slots_response(
    slots: list[dict[str, Any]] | None = None,
    as_dict: bool = False,
) -> list[dict[str, Any]] | dict[str, Any]:
    """
    Create a configurable slots response.

    Args:
        slots: List of slot dictionaries. If None, uses SLOTS_AVAILABLE.
        as_dict: If True, wraps slots in {"slots": [...]} dict format.

    Returns:
        Either a list of slots or a dict with "slots" key.
    """
    slot_list = slots if slots is not None else SLOTS_AVAILABLE
    if as_dict:
        return {"slots": slot_list}
    return slot_list
