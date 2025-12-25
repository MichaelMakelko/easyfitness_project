# api/routes.py
"""WhatsApp webhook routes and message handling."""

from typing import Any

from flask import Blueprint, jsonify, request

from api.whatsapp_client import send_whatsapp_message
from config import MAGICLINE_TEST_CUSTOMER_ID, VERIFY_TOKEN
from model.llama_model import LlamaBot
from services.booking_service import BookingService
from services.chat_service import ChatService
from services.customer_service import CustomerService
from utils.text_parser import (
    extract_booking_intent,
    extract_date_only,
    extract_date_time,
    extract_time_only,
)

# Initialize services
webhook_bp = Blueprint("webhook", __name__)
llm = LlamaBot()
customer_service = CustomerService()
chat_service = ChatService(llm)
booking_service = BookingService()

# Track processed message IDs to avoid duplicates (WhatsApp retries)
processed_message_ids: set[str] = set()


@webhook_bp.route("/webhook", methods=["GET"])
def verify() -> tuple[str, int]:
    """
    Verify webhook for WhatsApp API.

    Returns:
        Challenge string or error message with status code
    """
    if request.args.get("hub.verify_token") == VERIFY_TOKEN:
        return request.args.get("hub.challenge") or "", 200
    return "Falscher Token", 403


@webhook_bp.route("/webhook", methods=["POST"])
def webhook() -> tuple[Any, int]:
    """
    Handle incoming WhatsApp messages.

    Returns:
        JSON response with status code
    """
    data = request.get_json()
    print("📩 RAW DATA:", data)

    if not data or "entry" not in data:
        return jsonify(success=True), 200

    for entry in data.get("entry", []):
        for change in entry.get("changes", []):
            _process_change(change)

    return jsonify(success=True), 200


def _process_change(change: dict[str, Any]) -> None:
    """Process a single webhook change entry."""
    value = change.get("value", {})
    messages_list = value.get("messages", [])

    for msg in messages_list:
        # Skip duplicate messages (WhatsApp retries)
        msg_id = msg.get("id")
        if msg_id in processed_message_ids:
            print(f"⏭️ Duplikat ignoriert: {msg_id}")
            continue

        # Mark as processed
        processed_message_ids.add(msg_id)

        # Keep set size manageable (max 1000 entries)
        if len(processed_message_ids) > 1000:
            processed_message_ids.clear()

        if msg.get("type") == "text":
            _handle_text_message(
                phone=msg["from"],
                text=msg["text"]["body"],
            )


def _handle_text_message(phone: str, text: str) -> None:
    """
    Handle incoming text message from customer.

    Args:
        phone: Customer phone number
        text: Message text
    """
    try:
        # Get customer data
        print(f"📥 Verarbeite Nachricht von {phone}: {text}")
        customer = customer_service.get(phone)
        history = customer_service.get_history(phone, limit=12)

        # Generate response with profile extraction
        print("🤖 Generiere Antwort...")
        reply, extracted_profil = chat_service.generate_response(customer, history, text)
        print(f"✅ Antwort generiert: {reply[:100]}...")

        # Update profile if data was extracted
        if extracted_profil:
            customer_service.update_profil(phone, extracted_profil)
            print(f"📝 Profil aktualisiert: {extracted_profil}")

        # Update status if name was extracted
        if extracted_profil.get("name") and customer["name"] == "du":
            customer_service.update_status(phone, "Name bekannt")

        # Handle booking intent
        reply = _handle_booking_if_needed(phone, text, reply, extracted_profil, customer)

        # Save conversation and send reply
        customer_service.update_history(phone, text, reply)
        send_whatsapp_message(phone, reply)
        print(f"Max → {phone}: {reply}")

    except Exception as e:
        print(f"❌ FEHLER bei Nachricht von {phone}: {e}")
        import traceback
        traceback.print_exc()


def _handle_booking_if_needed(
    phone: str,
    text: str,
    reply: str,
    extracted_profil: dict[str, Any],
    customer: dict[str, Any],
) -> str:
    """
    Check for booking intent and process if needed.

    Args:
        phone: Customer phone number
        text: Customer message
        reply: Current bot reply
        extracted_profil: Extracted profile data
        customer: Customer data

    Returns:
        Updated reply with booking status
    """
    booking_intent = extract_booking_intent(text, reply)
    print(f"📅 Buchungs-Intent erkannt: {booking_intent}")

    if not booking_intent:
        return reply

    combined_text = (text + reply).lower()

    # Check what we have from the conversation
    probetraining_datum = extracted_profil.get("probetraining_datum")
    extracted_date = extract_date_only(combined_text)
    extracted_time = extract_time_only(combined_text)

    print(f"📅 Extrahiertes Datum: {extracted_date}")
    print(f"📅 Extrahierte Uhrzeit: {extracted_time}")

    # If we have date but no time, ask for time
    if extracted_date and not extracted_time and not probetraining_datum:
        print("⚠️ Datum vorhanden aber keine Uhrzeit - frage nach Uhrzeit")
        return f"{reply}\n\nUm welche Uhrzeit möchtest du am {_format_date_german(extracted_date)} vorbeikommen? 🕐"

    # Get full datetime
    start_date_time = probetraining_datum or extract_date_time(combined_text)

    print(f"📅 Vollständiges Datum/Zeit: {start_date_time}")

    if not start_date_time:
        print("⚠️ Kein vollständiges Datum/Zeit gefunden - Buchung übersprungen")
        return reply

    # Try to book (use test customer ID as fallback for unregistered users)
    customer_id = customer.get("profil", {}).get("magicline_customer_id") or MAGICLINE_TEST_CUSTOMER_ID
    print(f"📅 Versuche Buchung für Customer-ID: {customer_id}")

    success, message, booking_id = booking_service.try_book(
        customer_id=customer_id,
        start_datetime=start_date_time,
    )

    print(f"📅 Buchungsergebnis: success={success}, message={message}, booking_id={booking_id}")

    if success:
        customer["last_booking_id"] = booking_id
        customer_service.update_status(phone, "Probetraining gebucht")
        return f"{reply} ✅ {message}"
    else:
        return f"{reply} ❌ {message}"


def _format_date_german(date_str: str) -> str:
    """
    Format YYYY-MM-DD to German DD.MM.YYYY format.

    Args:
        date_str: Date in YYYY-MM-DD format

    Returns:
        Date in DD.MM.YYYY format
    """
    try:
        year, month, day = date_str.split("-")
        return f"{day}.{month}.{year}"
    except ValueError:
        return date_str
