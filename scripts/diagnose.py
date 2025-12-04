# diagnose.py  ←  Führe DAS jetzt aus (nicht die andere Datei)

import requests
from config import ACCESS_TOKEN, PHONE_NUMBER_ID

print("DIAGNOSE: WhatsApp Cloud API Test")
print(f"Phone Number ID: {PHONE_NUMBER_ID}")
print(f"Access Token (erste 30 Zeichen): {ACCESS_TOKEN[:30]}...")
print("-" * 50)

# 1. Teste, ob deine Nummer korrekt ist
url = f"https://graph.facebook.com/v20.0/{PHONE_NUMBER_ID}"
headers = {"Authorization": f"Bearer {ACCESS_TOKEN}"}
r = requests.get(url, headers=headers)

if r.status_code != 200:
    print("FEHLER: Phone Number ID oder Token falsch!")
    print(r.status_code, r.text)
    exit()

print("Phone Number ID + Token sind korrekt")

# 2. Teste echtes Senden an DICH SELBST (deine eigene Handynummer)
DEINE_NUMMER = "+49 163 5130654"   # ← Hier deine eigene Nummer eintragen, mit der du gerade chattest

payload = {
    "messaging_product": "whatsapp",
    "to": DEINE_NUMMER.replace("+", ""),
    "type": "text",
    "text": {"body": "DIAGNOSE: Dieser Test kommt direkt vom Bot – wenn alles stimmt!"}
}

r = requests.post(f"https://graph.facebook.com/v20.0/{PHONE_NUMBER_ID}/messages", 
                  json=payload, headers=headers)

print("\nAntwort von Meta:")
print(f"Status: {r.status_code}")
print(r.text)

if r.status_code == 200:
    print("\nALLES FUNKTIONIERT! Du solltest jetzt eine Nachricht auf deinem Handy sehen!")
else:
    print("\nFehlercodes und was sie bedeuten:")
    if "Error 130429" in r.text:
        print("→ Du bist im Sandbox-Modus und darfst nur an deine 5 Testnummern schreiben!")
        print("   Lösung: Gehe ins Meta Portal → WhatsApp → 'Send and receive messages' → Füge deine Nummer als Testnummer hinzu")
    elif "Error 131009" in r.text:
        print("→ Access Token abgelaufen oder falsch")
    elif "Error 100" in r.text:
        print("→ Ungültige Parameter – meist falsche Telefonnummer-Format")