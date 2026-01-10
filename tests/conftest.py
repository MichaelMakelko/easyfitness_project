"""Shared pytest fixtures for all tests."""

import json
import os
import sys
import tempfile
from pathlib import Path
from typing import Any, Generator
from unittest.mock import MagicMock, patch

# ==================== Environment Setup ====================
# IMPORTANT: Set test environment variables BEFORE any other imports
# This must happen at module level, before pytest fixtures run,
# because config.py loads .env immediately on import

os.environ["VERIFY_TOKEN"] = "test_verify_token"
os.environ["ACCESS_TOKEN"] = "test_access_token"
os.environ["PHONE_NUMBER_ID"] = "123456789"
os.environ["MODEL_PATH"] = "/fake/model/path"
os.environ["MAGICLINE_BASE_URL"] = "https://mock-api.magicline.com/v1"
os.environ["MAGICLINE_API_KEY"] = "test_api_key"
os.environ["MAGICLINE_BOOKABLE_ID_TRIAL_OFFER"] = "100"
os.environ["MAGICLINE_STUDIO_ID"] = "200"
os.environ["MAGICLINE_TRIAL_OFFER_CONFIG_ID"] = "300"
os.environ["MAGICLINE_TEST_CUSTOMER_ID"] = "999"

import pytest

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))


# ==================== Mock LLM Fixtures ====================

@pytest.fixture
def mock_llm():
    """Create a mock LLM model that returns configurable responses."""
    mock = MagicMock()
    mock.generate.return_value = '{"reply": "Hallo! Wie kann ich dir helfen?", "profil": {}}'
    return mock


@pytest.fixture
def mock_llm_with_extraction():
    """Mock LLM for extraction service testing."""
    mock = MagicMock()
    mock.generate.return_value = '{"vorname": "Max", "nachname": "Mustermann", "email": "max@test.de", "datum": "2025-01-15", "uhrzeit": "14:00"}'
    return mock


# ==================== Customer Data Fixtures ====================

@pytest.fixture
def sample_customer_new() -> dict[str, Any]:
    """Sample new customer data."""
    return {
        "name": "du",
        "status": "neuer Interessent",
        "profil": {
            "magicline_customer_id": None,
            "vorname": None,
            "nachname": None,
            "alter": None,
            "geschlecht": None,
            "wohnort": None,
            "beruf": None,
            "email": None,
            "fitness_ziel": None,
            "fitness_level": None,
            "fitness_erfahrung": None,
            "trainingsfrequenz": None,
            "aktuelles_studio": None,
            "gesundheitliche_einschraenkungen": None,
            "budget_bewusst": None,
            "zeitfenster": None,
            "entscheidungstraeger": None,
            "dringlichkeit": None,
            "wie_gefunden": None,
            "interesse_level": None,
            "beratungstermin_datum": None,
            "follow_up_datum": None,
        },
        "history": [],
        "letzter_kontakt": "01.01.2025 10:00",
    }


@pytest.fixture
def sample_customer_with_name() -> dict[str, Any]:
    """Sample customer with name known."""
    return {
        "name": "Max",
        "status": "Name bekannt",
        "profil": {
            "magicline_customer_id": None,
            "vorname": "Max",
            "nachname": "Mustermann",
            "alter": 30,
            "geschlecht": "maennlich",
            "wohnort": "Braunschweig",
            "beruf": None,
            "email": "max@test.de",
            "fitness_ziel": "Muskelaufbau",
            "fitness_level": None,
            "fitness_erfahrung": None,
            "trainingsfrequenz": None,
            "aktuelles_studio": None,
            "gesundheitliche_einschraenkungen": None,
            "budget_bewusst": None,
            "zeitfenster": None,
            "entscheidungstraeger": None,
            "dringlichkeit": None,
            "wie_gefunden": None,
            "interesse_level": None,
            "beratungstermin_datum": None,
            "follow_up_datum": None,
        },
        "history": [
            {"role": "user", "content": "Hallo!"},
            {"role": "assistant", "content": "Hey! Wie kann ich dir helfen?"},
        ],
        "letzter_kontakt": "15.01.2025 14:30",
    }


@pytest.fixture
def sample_customer_registered() -> dict[str, Any]:
    """Sample registered customer with MagicLine ID."""
    return {
        "name": "Anna",
        "status": "Beratungstermin gebucht",
        "profil": {
            "magicline_customer_id": 12345,
            "vorname": "Anna",
            "nachname": "Schmidt",
            "alter": 25,
            "geschlecht": "weiblich",
            "wohnort": "Braunschweig",
            "beruf": "Lehrerin",
            "email": "anna@test.de",
            "fitness_ziel": "Abnehmen",
            "fitness_level": "Anfaenger",
            "fitness_erfahrung": None,
            "trainingsfrequenz": None,
            "aktuelles_studio": None,
            "gesundheitliche_einschraenkungen": None,
            "budget_bewusst": None,
            "zeitfenster": "abends",
            "entscheidungstraeger": True,
            "dringlichkeit": "hoch",
            "wie_gefunden": "Instagram",
            "interesse_level": 5,
            "beratungstermin_datum": "2025-01-20T18:00:00+01:00",
            "follow_up_datum": None,
        },
        "history": [],
        "letzter_kontakt": "20.01.2025 18:00",
    }


# ==================== Temporary File Fixtures ====================

@pytest.fixture
def temp_customers_file() -> Generator[Path, None, None]:
    """Create a temporary customers.json file."""
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".json", delete=False, encoding="utf-8"
    ) as f:
        json.dump({}, f)
        temp_path = Path(f.name)

    yield temp_path

    # Cleanup
    if temp_path.exists():
        temp_path.unlink()


@pytest.fixture
def temp_customers_file_with_data(
    sample_customer_new, sample_customer_with_name
) -> Generator[Path, None, None]:
    """Create a temporary customers.json with sample data."""
    data = {
        "491234567890": sample_customer_new,
        "491111111111": sample_customer_with_name,
    }

    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".json", delete=False, encoding="utf-8"
    ) as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        temp_path = Path(f.name)

    yield temp_path

    if temp_path.exists():
        temp_path.unlink()


# ==================== DateTime Fixtures ====================

@pytest.fixture
def sample_datetime_iso() -> str:
    """Sample ISO datetime string."""
    return "2025-01-20T14:00:00+01:00"


# ==================== Prompt Template Fixture ====================

@pytest.fixture
def temp_prompt_file() -> Generator[Path, None, None]:
    """Create a temporary prompt template file."""
    prompt_content = """[SYSTEM]
Du bist Max, der freundliche WhatsApp-Assistent.

[AKTUELLES DATUM]
Heute ist {{WOCHENTAG}}, der {{DATUM}}.

[KUNDENDATEN]
Name: {{NAME}}
Status: {{STATUS}}
Bekanntes Profil: {{PROFIL}}

[BUCHUNGSSTATUS]
{{BUCHUNGSSTATUS}}

[AUSGABEFORMAT]
{"reply": "...", "profil": {...}}
"""

    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".txt", delete=False, encoding="utf-8"
    ) as f:
        f.write(prompt_content)
        temp_path = Path(f.name)

    yield temp_path

    if temp_path.exists():
        temp_path.unlink()
