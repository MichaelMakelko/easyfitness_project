"""WhatsApp webhook payload samples for testing."""

from typing import Any


def create_webhook_payload(
    phone: str = "491234567890",
    text: str = "Hallo!",
    message_id: str = "wamid.test123",
) -> dict[str, Any]:
    """Create a sample WhatsApp webhook payload."""
    return {
        "object": "whatsapp_business_account",
        "entry": [
            {
                "id": "123456789",
                "changes": [
                    {
                        "value": {
                            "messaging_product": "whatsapp",
                            "metadata": {
                                "display_phone_number": "4915123456789",
                                "phone_number_id": "123456789",
                            },
                            "contacts": [
                                {
                                    "profile": {"name": "Test User"},
                                    "wa_id": phone,
                                }
                            ],
                            "messages": [
                                {
                                    "from": phone,
                                    "id": message_id,
                                    "timestamp": "1704067200",
                                    "type": "text",
                                    "text": {"body": text},
                                }
                            ],
                        },
                        "field": "messages",
                    }
                ],
            }
        ],
    }


def create_status_update_payload() -> dict[str, Any]:
    """Create a status update webhook payload (no messages)."""
    return {
        "object": "whatsapp_business_account",
        "entry": [
            {
                "id": "123456789",
                "changes": [
                    {
                        "value": {
                            "messaging_product": "whatsapp",
                            "metadata": {
                                "display_phone_number": "4915123456789",
                                "phone_number_id": "123456789",
                            },
                            "statuses": [
                                {
                                    "id": "wamid.status123",
                                    "status": "delivered",
                                    "timestamp": "1704067200",
                                    "recipient_id": "491234567890",
                                }
                            ],
                        },
                        "field": "messages",
                    }
                ],
            }
        ],
    }


# Sample booking messages in German
BOOKING_MESSAGES = {
    "probetraining_with_datetime": "Ich moechte ein Probetraining am 20.01.2025 um 14:00 Uhr",
    "probetraining_date_only": "Kann ich am 20.01. vorbeikommen?",
    "probetraining_time_only": "Termin um 14 Uhr bitte",
    "probetraining_weekday": "Naechsten Montag Probetraining?",
    "termin_buchen": "Termin buchen fuer morgen 10:00",
    "just_greeting": "Hallo, wie geht es?",
    "price_question": "Was kostet das Training bei euch?",
}


# Sample name introduction messages
NAME_MESSAGES = {
    "ich_heisse": "Ich heisse Max Mustermann",
    "mein_name_ist": "Mein Name ist Anna Schmidt",
    "bin_der": "Ich bin der Thomas",
    "bin_die": "Bin die Maria",
    "ich_bin": "Ich bin Peter",
}
