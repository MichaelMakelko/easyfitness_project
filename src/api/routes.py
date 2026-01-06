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
    extract_full_name,
    extract_email,
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

        # === REGEX FALLBACK for unreliable LLM extraction ===
        # Names: LLM often misses or misspells names
        if not extracted_data.get("vorname") or not extracted_data.get("nachname"):
            regex_vorname, regex_nachname = extract_full_name(text)
            if regex_vorname and not extracted_data.get("vorname"):
                extracted_data["vorname"] = regex_vorname
                print(f"📝 Vorname (Regex): {regex_vorname}")
            if regex_nachname and not extracted_data.get("nachname"):
                extracted_data["nachname"] = regex_nachname
                print(f"📝 Nachname (Regex): {regex_nachname}")

        # Email: Regex is more reliable for email format
        if not extracted_data.get("email"):
            regex_email = extract_email(text)
            if regex_email:
                extracted_data["email"] = regex_email
                print(f"📝 Email (Regex): {regex_email}")

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

    Strategy:
    1. Load ALL stored profile data first
    2. Overlay with freshly extracted data from current message
    3. Check what's missing and either proceed to booking or ask for missing data

    Uses two different booking flows:
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
    profil = customer.get("profil", {})

    # === STEP 1: Load stored profile data ===
    stored_vorname = profil.get("vorname")
    stored_nachname = profil.get("nachname")
    stored_email = profil.get("email")
    stored_date = profil.get("datum")
    stored_time = profil.get("uhrzeit")

    # Check if ALL required data is already complete in profile
    all_data_complete = bool(
        stored_vorname and stored_nachname and stored_email and
        stored_date and stored_time
    )

    # Build customer context for booking intent detection
    has_booking_data = bool(stored_vorname and stored_nachname and stored_email)
    has_partial_datetime = bool(stored_date or stored_time)

    customer_context = {
        "has_booking_data": has_booking_data,
        "has_partial_datetime": has_partial_datetime,
    }

    booking_intent = extract_booking_intent(text, reply, customer_context)

    # IMPORTANT: If ALL data is complete, auto-trigger booking intent!
    # This handles cases where user provides the last missing piece (e.g., name/email)
    # without explicitly saying "buchen" again
    if all_data_complete and not booking_intent:
        print(f"📅 Alle Daten komplett - Auto-Trigger Buchung!")
        booking_intent = True

    print(f"📅 Buchungs-Intent: {booking_intent} (Kontext: {customer_context}, alle Daten komplett: {all_data_complete})")

    if not booking_intent:
        return reply

    # === STEP 2: Extract from current message ===
    # IMPORTANT: Regex FIRST (more reliable), then LLM for complex cases like "morgen"
    # This prevents LLM from returning wrong dates that override correct regex matches

    # Try regex first (reliable for explicit dates like "07.01.", "9.1 um 10")
    new_date = extract_date_only(text)
    new_time = extract_time_only(text)

    if new_date:
        print(f"📅 Datum (Regex): {new_date}")
    if new_time:
        print(f"📅 Uhrzeit (Regex): {new_time}")

    # LLM fallback for complex cases (e.g., "morgen", "nächsten Montag")
    if not new_date:
        llm_date = extracted_data.get("datum")
        if llm_date:
            new_date = llm_date
            print(f"📅 Datum (LLM-Fallback): {new_date}")

    if not new_time:
        llm_time = extracted_data.get("uhrzeit")
        if llm_time:
            new_time = llm_time
            print(f"📅 Uhrzeit (LLM-Fallback): {new_time}")

    # === STEP 3: Merge stored + new data (new takes priority) ===
    final_date = new_date or stored_date
    final_time = new_time or stored_time

    print(f"📅 Finales Datum: {final_date} (neu: {new_date}, gespeichert: {stored_date})")
    print(f"📅 Finale Uhrzeit: {final_time} (neu: {new_time}, gespeichert: {stored_time})")

    # Save new date/time to profile for future messages
    updates = {}
    if new_date and new_date != stored_date:
        updates["datum"] = new_date
    if new_time and new_time != stored_time:
        updates["uhrzeit"] = new_time
    if updates:
        customer_service.update_profil(phone, updates)
        print(f"📅 Profil aktualisiert: {updates}")

    # === STEP 4: Check what's missing ===
    # Check date/time first
    if final_date and not final_time:
        print("⚠️ Datum vorhanden aber keine Uhrzeit - frage nach Uhrzeit")
        date_german = format_date_german(final_date)
        return BotMessages.missing_time(date_german)

    if final_time and not final_date:
        print("⚠️ Uhrzeit vorhanden aber kein Datum - frage nach Datum")
        return "An welchem Tag möchtest du vorbeikommen? 📅"

    # Build full datetime
    start_date_time = build_datetime_iso(final_date, final_time)

    if not start_date_time:
        print("⚠️ Kein vollständiges Datum/Zeit gefunden - Buchung übersprungen")
        return reply

    print(f"📅 Vollständiges Datum/Zeit: {start_date_time}")

    # === STEP 5: Check personal data and proceed to booking ===
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

        # Get required data - use stored profile data!
        vorname = stored_vorname or (
            customer.get("name") if customer.get("name") != BotMessages.DEFAULT_NAME else None
        )
        nachname = stored_nachname
        email = stored_email

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
        # Determine booking type
        booking_type = "regular" if magicline_customer_id else "trial_offer"

        # Store complete booking record
        customer_service.add_booking(
            phone=phone,
            booking_id=booking_id,
            appointment_datetime=start_date_time,
            booking_type=booking_type,
        )
        customer_service.update_status(phone, CustomerStatus.TRIAL_BOOKED)
        print(f"📅 Buchung gespeichert: {booking_id} für {start_date_time}")
        # Use only system message to avoid redundancy
        return f"✅ {message}"
    else:
        # Don't use LLM reply - it might say "ich buche dich ein" which contradicts the error
        return f"❌ {message}"
