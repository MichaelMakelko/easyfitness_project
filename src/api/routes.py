# api/routes.py
"""WhatsApp webhook routes and message handling."""

from typing import Any

from flask import Blueprint, jsonify, request

from api.whatsapp_client import send_whatsapp_message
from config import VERIFY_TOKEN
from constants import (
    BotMessages,
    CustomerStatus,
    build_datetime_iso,
    format_date_german,
    message_tracker,
)
from model.llama_model import LlamaBot
from services.booking_service import BookingService
from services.chat_service import ChatService
from services.customer_service import CustomerService
from services.extraction_service import ExtractionService
from utils.text_parser import (
    extract_booking_intent,
    extract_date_only,
    extract_time_only,
)

# Initialize services
webhook_bp = Blueprint("webhook", __name__)
llm = LlamaBot()
customer_service = CustomerService()
chat_service = ChatService(llm)
booking_service = BookingService()
extraction_service = ExtractionService(llm)


@webhook_bp.route("/webhook", methods=["GET"])
def verify() -> tuple[str, int]:
    """
    Verify webhook for WhatsApp API.

    Returns:
        Challenge string or error message with status code
    """
    if request.args.get("hub.verify_token") == VERIFY_TOKEN:
        return request.args.get("hub.challenge") or "", 200
    return BotMessages.WRONG_TOKEN, 403


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
        msg_id = msg.get("id")

        # Skip duplicate messages using LRU-based tracker
        if message_tracker.is_duplicate(msg_id):
            print(f"⏭️ Duplikat ignoriert: {msg_id}")
            continue

        if msg.get("type") == "text":
            phone = msg.get("from")
            text_body = msg.get("text", {}).get("body")
            if phone and text_body:
                _handle_text_message(phone=phone, text=text_body)
            else:
                print(f"⚠️ Message missing required fields: from={phone}, text={text_body}")


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

        # Store original name to detect if we need status update later
        original_name = customer["name"]

        # Extract customer data from user message (LLM-based extraction)
        print("🔍 Extrahiere Kundendaten...")
        extracted_data = extraction_service.extract_customer_data(text)

        # Update profile with extracted data
        if any(v for v in extracted_data.values() if v):
            customer_service.update_profil(phone, extracted_data)
            print(f"📝 Profil aktualisiert: {extracted_data}")
            # Refresh customer data after update
            customer = customer_service.get(phone)

        # Generate response
        print("🤖 Generiere Antwort...")
        reply, extracted_profil = chat_service.generate_response(customer, history, text)
        print(f"✅ Antwort generiert: {reply[:100]}...")

        # Update profile if LLM also extracted data (merge with existing)
        if extracted_profil:
            customer_service.update_profil(phone, extracted_profil)
            print(f"📝 Profil (LLM) aktualisiert: {extracted_profil}")

        # Update status if name was extracted and customer was previously unknown
        # Use original_name to avoid race condition after profile update
        vorname_found = extracted_data.get("vorname") or extracted_profil.get("vorname")
        if vorname_found and original_name == BotMessages.DEFAULT_NAME:
            customer_service.update_status(phone, CustomerStatus.NAME_KNOWN)

        # Refresh customer data before booking check to get latest profile
        customer = customer_service.get(phone)

        # Handle booking intent (pass extracted_data for date/time)
        reply = _handle_booking_if_needed(phone, text, reply, extracted_data, customer)

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
    extracted_data: dict[str, Any],
    customer: dict[str, Any],
) -> str:
    """
    Check for booking intent and process if needed.

    Uses two different flows:
    1. Regular booking: If customer has magicline_customer_id
    2. Trial offer booking: If customer is a new lead (no magicline_customer_id)

    Args:
        phone: Customer phone number
        text: Customer message
        reply: Current bot reply
        extracted_data: LLM-extracted data (vorname, nachname, email, datum, uhrzeit)
        customer: Customer data

    Returns:
        Updated reply with booking status
    """
    # Build customer context for booking intent detection
    profil = customer.get("profil", {})
    has_booking_data = bool(
        profil.get("vorname") and
        profil.get("nachname") and
        profil.get("email")
    )
    has_partial_datetime = bool(profil.get("datum") or profil.get("uhrzeit"))

    customer_context = {
        "has_booking_data": has_booking_data,
        "has_partial_datetime": has_partial_datetime,
    }

    booking_intent = extract_booking_intent(text, reply, customer_context)
    print(f"📅 Buchungs-Intent erkannt: {booking_intent} (Kontext: {customer_context})")

    if not booking_intent:
        return reply

    # === HYBRID EXTRACTION: LLM + Regex Fallback ===
    # Try LLM extraction first
    extracted_date = extracted_data.get("datum")
    extracted_time = extracted_data.get("uhrzeit")

    # Regex fallback if LLM failed
    if not extracted_date:
        extracted_date = extract_date_only(text)
        if extracted_date:
            print(f"📅 Datum (Regex-Fallback): {extracted_date}")
            # Save to profile for context
            customer_service.update_profil(phone, {"datum": extracted_date})

    if not extracted_time:
        extracted_time = extract_time_only(text)
        if extracted_time:
            print(f"📅 Uhrzeit (Regex-Fallback): {extracted_time}")

    print(f"📅 Extrahiertes Datum: {extracted_date}")
    print(f"📅 Extrahierte Uhrzeit: {extracted_time}")

    # === CONTEXT: Use stored values from profile if missing ===
    profil = customer.get("profil", {})

    # If we have time but no date, check if there's a stored date
    if extracted_time and not extracted_date:
        stored_date = profil.get("datum")
        if stored_date:
            extracted_date = stored_date
            print(f"📅 Verwende gespeichertes Datum: {extracted_date}")

    # If we have date but no time, ask for time
    if extracted_date and not extracted_time:
        # Store the date for next message
        customer_service.update_profil(phone, {"datum": extracted_date})
        print("⚠️ Datum vorhanden aber keine Uhrzeit - frage nach Uhrzeit")
        date_german = format_date_german(extracted_date)
        return BotMessages.missing_time(date_german)

    # Build full datetime
    start_date_time = build_datetime_iso(extracted_date, extracted_time)

    print(f"📅 Vollständiges Datum/Zeit: {start_date_time}")

    if not start_date_time:
        print("⚠️ Kein vollständiges Datum/Zeit gefunden - Buchung übersprungen")
        return reply

    # Check if customer has MagicLine ID (registered customer)
    profil = customer.get("profil", {})
    magicline_customer_id = profil.get("magicline_customer_id")

    if magicline_customer_id:
        # ===== REGISTERED CUSTOMER FLOW =====
        print(f"📅 Registrierter Kunde - verwende Customer-ID: {magicline_customer_id}")
        success, message, booking_id = booking_service.try_book(
            customer_id=magicline_customer_id,
            start_datetime=start_date_time,
        )
    else:
        # ===== TRIAL OFFER FLOW (für neue Leads) =====
        print("📅 Neuer Lead - verwende Trial Offer Flow")

        # Get required data for trial offer booking
        vorname = profil.get("vorname") or (
            customer.get("name") if customer.get("name") != BotMessages.DEFAULT_NAME else None
        )
        nachname = profil.get("nachname")
        email = profil.get("email")

        # Check for missing required data
        missing_fields = []
        if not vorname:
            missing_fields.append("Vorname")
        if not nachname:
            missing_fields.append("Nachname")
        if not email:
            missing_fields.append("E-Mail-Adresse")

        if missing_fields:
            print(f"⚠️ Fehlende Daten für Trial Offer: {', '.join(missing_fields)}")
            # Don't use LLM reply - it might say "ich buche dich ein" which is misleading
            return BotMessages.missing_booking_data(missing_fields)

        print(f"📅 Trial Offer Buchung: {vorname} {nachname} ({email})")
        success, message, booking_id = booking_service.try_book_trial_offer(
            first_name=vorname,
            last_name=nachname,
            email=email,
            start_datetime=start_date_time,
        )

    print(f"📅 Buchungsergebnis: success={success}, message={message}, booking_id={booking_id}")

    if success:
        # Persist booking_id to customer profile
        customer_service.update_profil(phone, {"last_booking_id": booking_id})
        customer_service.update_status(phone, CustomerStatus.TRIAL_BOOKED)
        # Use only system message to avoid redundancy
        return f"✅ {message}"
    else:
        # Don't use LLM reply - it might say "ich buche dich ein" which contradicts the error
        return f"❌ {message}"
