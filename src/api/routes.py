# api/routes.py
"""WhatsApp webhook routes and message handling."""

from typing import Any

from flask import Blueprint, jsonify, request

from api.whatsapp_client import send_whatsapp_message
from config import VERIFY_TOKEN
from model.llama_model import LlamaBot
from services.booking_service import BookingService
from services.chat_service import ChatService
from services.customer_service import CustomerService
from utils.text_parser import extract_booking_intent, extract_date_time

# Initialize services
webhook_bp = Blueprint("webhook", __name__)
llm = LlamaBot()
customer_service = CustomerService()
chat_service = ChatService(llm)
booking_service = BookingService()


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
    # Get customer data
    customer = customer_service.get(phone)
    history = customer_service.get_history(phone, limit=12)

    # Generate response with profile extraction
    reply, extracted_profil = chat_service.generate_response(customer, history, text)

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
    if not extract_booking_intent(text, reply):
        return reply

    # Get email from profile or legacy location
    customer_email = customer.get("profil", {}).get("email") or customer.get("email")

    # Get booking datetime
    probetraining_datum = extracted_profil.get("probetraining_datum")
    start_date_time = probetraining_datum or extract_date_time(
        (text + reply).lower()
    )

    if not start_date_time or not customer_email:
        return reply

    # Try to book
    customer_id = customer.get("customer_id", 0)
    success, message, booking_id = booking_service.try_book(
        customer_id=customer_id,
        start_datetime=start_date_time,
    )

    if success:
        customer["last_booking_id"] = booking_id
        customer_service.update_status(phone, "Probetraining gebucht")
        return f"{reply} ✅ {message}"
    else:
        return f"{reply} ❌ {message}"
