# whatsapp/client.py
import requests
from config import ACCESS_TOKEN, PHONE_NUMBER_ID

def send_whatsapp_message(to, text):
    """Normale Antwort (innerhalb 24h oder auf eingehende Nachricht)"""
    url = f"https://graph.facebook.com/v22.0/{PHONE_NUMBER_ID}/messages"
    headers = {"Authorization": f"Bearer {ACCESS_TOKEN}"}
    payload = {
        "messaging_product": "whatsapp",
        "to": to,
        "type": "text",
        "text": {"body": text}
    }
    r = requests.post(url, json=payload, headers=headers)
    if r.status_code != 200:
        print("Fehler beim Senden:", r.text)

def send_template_message(to: str, name: str = "du"):
    """
    Schickt eine Template-Nachricht – funktioniert IMMER im Testmodus!
    Auch als allererste Nachricht an eine neue Nummer.
    """
    url = f"https://graph.facebook.com/v22.0/{PHONE_NUMBER_ID}/messages"
    headers = {"Authorization": f"Bearer {ACCESS_TOKEN}"}

    payload = {
        "messaging_product": "whatsapp",
        "to": to.replace("+", ""),   # z.B. 491635130654
        "type": "template",
        "template": {
            "name": "jaspers_market_plain_text_v1",   # ← dein existierendes Template
            "language": {"code": "en_US"},
        }
    }

    r = requests.post(url, json=payload, headers=headers)
    if r.status_code == 200:
        print(f"TEMPLATE-NACHRICHT GESENDET an {to}!")
        print("Du siehst sie in 3–10 Sekunden auf deinem Handy")
    else:
        print("Fehler:", r.status_code, r.text)

# whatsapp/client.py – erweitert
def send_free_message(to: str, text: str):
    """
    Schickt eine freie Textnachricht – NUR innerhalb der 24h-Fensters!
    Funktioniert sofort, kein Template nötig.
    """
    url = f"https://graph.facebook.com/v22.0/{PHONE_NUMBER_ID}/messages"
    headers = {"Authorization": f"Bearer {ACCESS_TOKEN}"}
    payload = {
        "messaging_product": "whatsapp",
        "to": to.replace("+", ""),
        "type": "text",
        "text": {"body": text}
    }
    r = requests.post(url, json=payload, headers=headers)
    if r.status_code == 200:
        print(f"Freie Nachricht gesendet an {to}")
    else:
        print(f"Fehler (vielleicht 24h abgelaufen?): {r.status_code} – {r.text}")


def send_outbound_message(to: str, text: str):
    """Schickt die allererste Nachricht an eine neue Nummer – danach übernimmt der Bot automatisch"""
    url = f"https://graph.facebook.com/v22.0/{PHONE_NUMBER_ID}/messages"
    headers = {"Authorization": f"Bearer {ACCESS_TOKEN}"}
    payload = {
        "messaging_product": "whatsapp",
        "to": to.replace("+", ""),
        "type": "text",
        "text": {"body": text}
    }
    r = requests.post(url, json=payload, headers=headers)
    if r.status_code == 200:
        print(f"Erste Nachricht gesendet an {to} – Bot übernimmt jetzt!")
    else:
        print(f"Fehler: {r.status_code} → {r.text}")