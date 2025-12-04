# send_with_template.py  ← STARTE DAS JETZT!

from whatsapp.client import send_template_message
from memory.customer_db import CustomerDB

db = CustomerDB()

# =================================================
# HIER NUMMER + NAME EINTRAGEN
# =================================================
zielnummer = "+491635130654"      # ← deine Handynummer
vorname     = "Mika"              # ← dein Name (oder "Anna", "Max", etc.)

# =================================================
send_template_message(zielnummer)

# Nummer automatisch ins Gedächtnis speichern
if zielnummer not in db.customers:
    db.customers[zielnummer] = {
        "name": vorname,
        "status": "per Template angeschrieben",
        "history": [],
        "letzter_kontakt": "jetzt"
    }
    db.save()

print("Fertig! Schau auf dein Handy – die Nachricht kommt SOFORT!")