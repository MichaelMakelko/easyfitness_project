# memory/customer_db.py
import json
import os
from datetime import datetime

MEMORY_FILE = "data/customers.json"

class CustomerDB:
    def __init__(self):
        self.customers = self._load()

    def _load(self):
        if os.path.exists(MEMORY_FILE):
            with open(MEMORY_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        return {}

    def save(self):
        with open(MEMORY_FILE, "w", encoding="utf-8") as f:
            json.dump(self.customers, f, indent=2, ensure_ascii=False)

    def get(self, phone):
        if phone not in self.customers:
            self.customers[phone] = {
                "name": "du",
                "status": "neuer Interessent",
                "history": [],
                "letzter_kontakt": datetime.now().strftime("%d.%m.%Y %H:%M")
            }
            self.save()
        return self.customers[phone]

    def update_history(self, phone, user_msg, bot_reply):
        customer = self.get(phone)
        customer["history"].append({"role": "user", "content": user_msg})
        customer["history"].append({"role": "assistant", "content": bot_reply})
        if len(customer["history"]) > 100:  # nicht ewig wachsen lassen
            customer["history"] = customer["history"][-80:]
        customer["letzter_kontakt"] = datetime.now().strftime("%d.%m.%Y %H:%M")
        self.save()