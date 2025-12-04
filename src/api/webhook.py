# whatsapp/webhook.py
import re
from flask import Blueprint, request, jsonify
from model.llama_model import LlamaBot
from services.memory.customer_db import CustomerDB
from api.client import send_whatsapp_message
from utils.helpers import extract_name
from config import VERIFY_TOKEN
import requests

from utils.helpers import extract_name, extract_booking_intent, extract_date_time
from config import MAGICLINE_BASE_URL, MAGICLINE_API_KEY, MAGICLINE_BOOKABLE_ID

webhook_bp = Blueprint('webhook', __name__)
llm = LlamaBot()
db = CustomerDB()

def build_messages(customer):
    # Aktualisierter Prompt: Frage nach Name, E-Mail, Datum für Probetraining
    name = customer["name"] if customer["name"] != "du" else "noch unbekannt"
    email = customer.get("email", "noch unbekannt")
    system_prompt = f"""Du bist Max, der mega freundliche Chatbot von easyfitness EMS.
Kunde: {name} | Status: {customer['status']}
Wenn Probetraining gewünscht: Frage nach Name (wenn unbekannt), E-Mail, gewünschtem Datum/Uhrzeit (z.B. 12.12.2024 15:00).
Sobald alle Infos da: Sage 'Super, ich buche das für dich!'.
Antworte locker, mit Emojis, maximal 2–3 kurze Sätze."""
    messages = [{"role": "system", "content": system_prompt}]
    messages.extend(customer["history"][-12:])
    return messages

@webhook_bp.route("/webhook", methods=['GET'])
def verify():
    if request.args.get("hub.verify_token") == VERIFY_TOKEN:
        return request.args.get("hub.challenge") or "", 200
    return "Falscher Token", 403

@webhook_bp.route("/webhook", methods=['POST'])
def webhook():
    data = request.get_json()
    print("📩 RAW DATA:", data)  # ← Diese Zeile hinzufügen
    if not data or "entry" not in data:
        return jsonify(success=True), 200

    for entry in data.get("entry", []):
        for change in entry.get("changes", []):
            value = change.get("value", {})
            messages_list = value.get("messages", [])
            for msg in messages_list:
                if msg.get("type") == "text":
                    phone = msg["from"]
                    text = msg["text"]["body"]

                    customer = db.get(phone)
                    prompt_messages = build_messages(customer)
                    prompt_messages.append({"role": "user", "content": text})

                    reply = llm.generate(prompt_messages)

                    # Name erkennen (wie bisher)
                    new_name = extract_name(text)
                    if new_name and customer["name"] == "du":
                        customer["name"] = new_name
                        customer["status"] = "Name bekannt"

                    # E-Mail erkennen (einfach, erweiterbar)
                    email_match = re.search(r'[\w\.-]+@[\w\.-]+', text.lower())
                    if email_match and "email" not in customer:
                        customer["email"] = email_match.group(0)

                    # Buchungs-Intent erkennen und API aufrufen
                    if extract_booking_intent(text, reply):
                        start_date_time = extract_date_time(text.lower() + reply.lower())
                        if start_date_time and "email" in customer:
                            # 1. Validieren (POST /appointments/bookable/validate)
                            validate_payload = {
                                "customerId": customer.get("customer_id", 0),  # Hole aus MagicLine oder erstelle Customer zuerst
                                "bookableAppointmentId": MAGICLINE_BOOKABLE_ID,
                                "startDateTime": start_date_time,
                                "endDateTime": start_date_time.replace("00:00", "00:20")  # 20 Min EMS
                            }
                            headers = {"X-API-KEY": MAGICLINE_API_KEY, "Content-Type": "application/json"}
                            validate_response = requests.post(f"{MAGICLINE_BASE_URL}/appointments/bookable/validate", json=validate_payload, headers=headers)
                            if validate_response.json().get("validationStatus") == "AVAILABLE":
                                # 2. Buchen (POST /appointments/booking/book)
                                book_response = requests.post(f"{MAGICLINE_BASE_URL}/appointments/booking/book", json=validate_payload, headers=headers)
                                if book_response.status_code == 200:
                                    booking_id = book_response.json().get("bookingId")
                                    customer["last_booking_id"] = booking_id
                                    reply += " ✅ Termin gebucht! Bestätigung per E-Mail unterwegs."
                                    # send_confirmation_email(customer["email"], customer["name"], start_date_time)
                                else:
                                    reply += " ❌ Leider nicht verfügbar – wähle ein anderes Datum."
                            else:
                                reply += " ❌ Slot nicht verfügbar – probier ein anderes Datum."

                    db.update_history(phone, text, reply)
                    send_whatsapp_message(phone, reply)
                    print(f"Max → {phone}: {reply}")

    return jsonify(success=True), 200


