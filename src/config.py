# config.py
import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file
BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")

# WhatsApp API Configuration
VERIFY_TOKEN: str = os.getenv("VERIFY_TOKEN", "")
ACCESS_TOKEN: str = os.getenv("ACCESS_TOKEN", "")
PHONE_NUMBER_ID: str = os.getenv("PHONE_NUMBER_ID", "")

# Model Configuration
MODEL_PATH: str = os.getenv("MODEL_PATH", "")

# File Paths (absolute)
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(exist_ok=True)
MEMORY_FILE: Path = DATA_DIR / "customers.json"
PROMPTS_DIR: Path = BASE_DIR / "src" / "prompts"

# MagicLine API
MAGICLINE_BASE_URL: str = os.getenv("MAGICLINE_BASE_URL", "https://open-api.magicline.com/v1")
MAGICLINE_API_KEY: str = os.getenv("MAGICLINE_API_KEY", "")
MAGICLINE_BOOKABLE_ID: int = int(os.getenv("MAGICLINE_BOOKABLE_ID", "0"))
MAGICLINE_STUDIO_ID: int = int(os.getenv("MAGICLINE_STUDIO_ID", "0"))
MAGICLINE_TEST_CUSTOMER_ID: int = int(os.getenv("MAGICLINE_TEST_CUSTOMER_ID", "0"))
MAGICLINE_TRIAL_OFFER_CONFIG_ID: int = int(os.getenv("MAGICLINE_TRIAL_OFFER_CONFIG_ID", "0"))

# Email Configuration (optional)
EMAIL_SENDER: str = os.getenv("EMAIL_SENDER", "")
EMAIL_PASSWORD: str = os.getenv("EMAIL_PASSWORD", "")
EMAIL_SMTP_SERVER: str = os.getenv("EMAIL_SMTP_SERVER", "smtp.gmail.com")
EMAIL_SMTP_PORT: int = int(os.getenv("EMAIL_SMTP_PORT", "587"))
