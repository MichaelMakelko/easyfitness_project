"""Customer data samples for testing."""

from typing import Any


def create_default_profil() -> dict[str, Any]:
    """Create default empty customer profile."""
    return {
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
    }


def create_customer(
    name: str = "du",
    status: str = "neuer Interessent",
    profil_updates: dict[str, Any] | None = None,
    history: list[dict[str, str]] | None = None,
) -> dict[str, Any]:
    """Create a configurable customer record."""
    profil = create_default_profil()
    if profil_updates:
        profil.update(profil_updates)

    return {
        "name": name,
        "status": status,
        "profil": profil,
        "history": history or [],
        "letzter_kontakt": "01.01.2025 10:00",
    }


# Pre-built customer scenarios
CUSTOMER_NEW_LEAD = create_customer()

CUSTOMER_WITH_NAME = create_customer(
    name="Max",
    status="Name bekannt",
    profil_updates={
        "vorname": "Max",
        "nachname": "Mustermann",
        "email": "max@test.de",
    },
)

CUSTOMER_READY_TO_BOOK = create_customer(
    name="Anna",
    status="Name bekannt",
    profil_updates={
        "vorname": "Anna",
        "nachname": "Schmidt",
        "email": "anna@test.de",
    },
    history=[
        {"role": "user", "content": "Hallo!"},
        {"role": "assistant", "content": "Hey Anna!"},
    ],
)

CUSTOMER_REGISTERED = create_customer(
    name="Peter",
    status="Beratungstermin gebucht",
    profil_updates={
        "magicline_customer_id": 12345,
        "vorname": "Peter",
        "nachname": "Mueller",
        "email": "peter@test.de",
    },
)
