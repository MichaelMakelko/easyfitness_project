# start_chat_with_anyone.py
# → Du schreibst eine neue Nummer an → Bot speichert sie + übernimmt ab sofort

from whatsapp.client import send_outbound_message
from memory.customer_db import CustomerDB

db = CustomerDB()

# =========================================
# HIER NUMMER + ERSTE NACHRICHT EINTRAGEN
# =========================================
neue_nummer = "+491635130654"   # ← echte Nummer von Kunde/Freund
erste_nachricht = """Hey Mika!

Hier ist Max von easyfitness EMS in Köln

Wir haben gerade eine mega Aktion: 4 Wochen EMS nur 99 € – und du kannst jederzeit ein kostenloses Probetraining machen!

Magst du direkt einen Termin? Einfach „Ja“ schreiben!"""

# =========================================
# Nicht ändern – nur ausführen!
# =========================================
send_outbound_message(neue_nummer, erste_nachricht)

# Nummer wird automatisch ins Gedächtnis aufgenommen (falls noch nicht da)
if neue_nummer not in db.customers:
    db.customers[neue_nummer] = {
        "name": "du",
        "status": "neuer Interessent (aktiv angeschrieben)",
        "history": [],
        "letzter_kontakt": "jetzt"
    }
    db.save()

print(f"\nNummer {neue_nummer} gespeichert!")
print("Sobald der Kunde antwortet, übernimmt Max automatisch den ganzen Chat")
print("Du kannst später jederzeit wieder mit send_now.py oder Kampagne schreiben")