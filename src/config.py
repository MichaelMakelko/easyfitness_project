# config.py
VERIFY_TOKEN = "easyfitness2025_supersecret"
ACCESS_TOKEN = "EAAWDqhvpON8BQNoZBsF1pA4V5p5TJ1E9V50ySiQAHEzZBiuOGicUafWexmZA7OJxZAb5Nfh9s7m9jKL8oFk8XtZCEQTCs37buKsWeKDF2kEhMhxqpjZBRWguHeA72ZBZCNh1LzZC0fj0vvMZCWgymZC3k36ZBaiKRAZBSkbcFqZC7dGDBzaj9W698ehBnEgyEuFH3AoFub6q8eMXMgtdRIduz5cF117qZBQJ2nomoc3IVbB"           # ← eintragen
PHONE_NUMBER_ID = "933710443155490"              # ← eintragen

MODEL_PATH = r"D:\Github\llama_model_ems\hf_hub\models--meta-llama--Llama-3.1-8B-Instruct"
MEMORY_FILE = "data/customers.json"

import os
os.makedirs("data", exist_ok=True)


# MagicLine API
MAGICLINE_BASE_URL = "https://open-api.magicline.com/v1"  # Oder deine Demo/Prod-URL
MAGICLINE_API_KEY = "dein_magicline_api_key_hier"  # Hole aus Developer Portal
MAGICLINE_BOOKABLE_ID = 12345  # ID deines "Probetraining EMS" Appointments (aus MagicLine holen)
MAGICLINE_STUDIO_ID = 67890  # Deine Studio-ID


# # E-Mail Config (für Bestätigung)
# EMAIL_SENDER = "dein.studio@gmail.com"
# EMAIL_PASSWORD = "dein_app_password"
# EMAIL_SMTP_SERVER = "smtp.gmail.com"
# EMAIL_SMTP_PORT = 587
