# MagicLine OpenAPI Documentation

Diese Dokumentation fasst das Wissen über die MagicLine OpenAPI zusammen, das für die EasyFitness Chatbot-Integration relevant ist.

## Übersicht

MagicLine ist eine Fitness-Studio-Management-Software der Sport Alliance. Die OpenAPI ermöglicht die Integration von Buchungssystemen, Lead-Management und Terminverwaltung.

**API Base URL:** Konfiguriert über `MAGICLINE_BASE_URL` Environment Variable
**Authentifizierung:** API-Key Header (`X-Api-Key` oder via `MAGICLINE_API_KEY`)

---

## Trial Offers API

Die Trial Offers API ermöglicht das Buchen von Probetrainings für neue Leads (Interessenten ohne bestehenden MagicLine-Account).

### Endpoints

#### 1. GET Slot Availability
```
GET /trial-offers/appointments/{bookableAppointmentId}/slots
```

**Beschreibung:** Prüft verfügbare Zeitslots für ein Probetraining an einem bestimmten Tag.

**Path Parameter:**
| Parameter | Typ | Beschreibung |
|-----------|-----|--------------|
| `bookableAppointmentId` | integer | ID des buchbaren Termins (z.B. Probetraining) |

**Query Parameter:**
| Parameter | Typ | Default | Beschreibung |
|-----------|-----|---------|--------------|
| `date` | string | - | Datum im Format `YYYY-MM-DD` |
| `duration` | integer | 30 | Dauer in Minuten |

**Response (200 OK):**
```json
[
  {
    "startDateTime": "2025-01-20T09:00:00+01:00",
    "endDateTime": "2025-01-20T09:30:00+01:00"
  },
  {
    "startDateTime": "2025-01-20T10:00:00+01:00",
    "endDateTime": "2025-01-20T10:30:00+01:00"
  }
]
```

**Wichtig:**
- Response ist ein Array (keine Wrapper-Objekt)
- Leeres Array `[]` bedeutet keine verfügbaren Slots
- Zeiten sind im ISO 8601 Format mit Timezone-Offset

---

#### 2. POST Validate Lead
```
POST /trial-offers/lead/validate
```

**Beschreibung:** Validiert Lead-Daten vor der Erstellung (E-Mail-Format, Duplikatprüfung).

**Request Body:**
```json
{
  "studioId": 12345,
  "trialOfferConfigId": 67890,
  "firstName": "Max",
  "lastName": "Mustermann",
  "email": "max@test.de"
}
```

**Response (200 OK - Erfolg):**
```json
{
  "valid": true,
  "message": "Lead data is valid"
}
```

**Response (200 OK - Fehler):**
```json
{
  "valid": false,
  "message": "Invalid email format"
}
```

---

#### 3. POST Create Lead
```
POST /trial-offers/lead/create
```

**Beschreibung:** Erstellt einen neuen Lead im MagicLine-System.

**Request Body:**
```json
{
  "studioId": 12345,
  "trialOfferConfigId": 67890,
  "firstName": "Max",
  "lastName": "Mustermann",
  "email": "max@test.de"
}
```

**Response (200 OK - Erfolg):**
```json
{
  "success": true,
  "leadCustomerId": 67890,
  "status": "CREATED"
}
```

**Response (200 OK - Fehler):**
```json
{
  "success": false,
  "error": "Lead creation failed",
  "reason": "Duplicate email"
}
```

**Wichtig:** Die `leadCustomerId` wird für alle weiteren Buchungsschritte benötigt.

---

## Appointments API

Die Appointments API wird sowohl für Bestandskunden als auch für Leads verwendet.

### Endpoints

#### 4. POST Validate Appointment
```
POST /appointments/bookable/validate
```

**Beschreibung:** Prüft, ob ein Termin zu einer bestimmten Zeit buchbar ist.

**Request Body:**
```json
{
  "bookableAppointmentId": 12345,
  "customerId": 67890,
  "startDateTime": "2025-01-20T14:00:00+01:00",
  "endDateTime": "2025-01-20T14:30:00+01:00"
}
```

**Response (200 OK - Verfügbar):**
```json
{
  "validationStatus": "AVAILABLE",
  "slotDetails": {
    "startDateTime": "2025-01-20T14:00:00+01:00",
    "endDateTime": "2025-01-20T14:30:00+01:00"
  }
}
```

**Response (200 OK - Nicht verfügbar):**
```json
{
  "validationStatus": "NOT_AVAILABLE",
  "reason": "Slot already booked"
}
```

**Validation Status Werte:**
| Status | Bedeutung |
|--------|-----------|
| `AVAILABLE` | Slot ist buchbar |
| `NOT_AVAILABLE` | Slot ist belegt |
| `ERROR` | Validierungsfehler |

---

#### 5. POST Book Appointment
```
POST /appointments/booking/book
```

**Beschreibung:** Führt die eigentliche Buchung durch.

**Request Body:**
```json
{
  "bookableAppointmentId": 12345,
  "customerId": 67890,
  "startDateTime": "2025-01-20T14:00:00+01:00",
  "endDateTime": "2025-01-20T14:30:00+01:00"
}
```

**Response (200 OK - Erfolg):**
```json
{
  "bookingId": 1234567890,
  "status": "CONFIRMED",
  "startDateTime": "2025-01-20T14:00:00+01:00",
  "endDateTime": "2025-01-20T14:30:00+01:00"
}
```

**Response (200 OK - Fehler):**
```json
{
  "error": "Booking failed",
  "reason": "Slot no longer available"
}
```

---

## Buchungsflows

### Flow 1: Bestandskunde (hat `magicline_customer_id`)

```
┌─────────────────────────────────────┐
│ 1. POST /appointments/bookable/validate │
│    → Prüft Slot-Verfügbarkeit           │
└───────────────┬─────────────────────────┘
                │
                ▼
┌─────────────────────────────────────┐
│ 2. POST /appointments/booking/book  │
│    → Bucht den Termin               │
└─────────────────────────────────────┘
```

**Benötigte Daten:**
- `customerId` (MagicLine Customer ID)
- `startDateTime`, `endDateTime`
- `bookableAppointmentId`

---

### Flow 2: Trial Offer (neuer Lead ohne `magicline_customer_id`)

```
┌─────────────────────────────────────────────┐
│ 0. GET /trial-offers/appointments/.../slots │  ◄── NEU: Pre-Check
│    → Prüft ob Slot überhaupt existiert      │
└───────────────┬─────────────────────────────┘
                │ (Slot verfügbar?)
                ▼
┌─────────────────────────────────────┐
│ 1. POST /trial-offers/lead/validate │
│    → Validiert Lead-Daten           │
└───────────────┬─────────────────────┘
                │
                ▼
┌─────────────────────────────────────┐
│ 2. POST /trial-offers/lead/create   │
│    → Erstellt Lead → leadCustomerId │
└───────────────┬─────────────────────┘
                │
                ▼
┌─────────────────────────────────────────────┐
│ 3. POST /appointments/bookable/validate     │
│    → Prüft Slot (mit leadCustomerId)        │
└───────────────┬─────────────────────────────┘
                │
                ▼
┌─────────────────────────────────────┐
│ 4. POST /appointments/booking/book  │
│    → Bucht Termin                   │
└─────────────────────────────────────┘
```

**Benötigte Daten:**
- `vorname`, `nachname`, `email` (für Lead-Erstellung)
- `startDateTime`, `endDateTime`
- `studioId`, `trialOfferConfigId`, `bookableAppointmentId`

---

## Environment Variables

| Variable | Beschreibung | Beispiel |
|----------|--------------|----------|
| `MAGICLINE_BASE_URL` | API Base URL | `https://api.magicline.com/v1` |
| `MAGICLINE_API_KEY` | API Authentifizierung | `sk-...` |
| `MAGICLINE_BOOKABLE_ID` | ID für Probetraining-Termine | `100` |
| `MAGICLINE_STUDIO_ID` | Studio-ID | `12345` |
| `MAGICLINE_TRIAL_OFFER_CONFIG_ID` | Trial Offer Konfiguration | `67890` |
| `MAGICLINE_TEST_CUSTOMER_ID` | Test-Kunden-ID für Development | `99999` |

---

## Fehlerbehandlung

### HTTP Status Codes

| Code | Bedeutung | Handling |
|------|-----------|----------|
| 200 | Erfolg (auch bei business-logic Fehlern) | Response Body prüfen |
| 400 | Bad Request | Ungültige Parameter |
| 401 | Unauthorized | API-Key prüfen |
| 404 | Not Found | Endpoint/Resource nicht gefunden |
| 500 | Server Error | Retry oder Fallback |

### Business Logic Fehler (200 OK)

Die API gibt HTTP 200 auch bei Business-Logic-Fehlern zurück. Der Response Body enthält dann:
- `validationStatus: "NOT_AVAILABLE"` bei Slot-Konflikten
- `success: false` bei Lead-Erstellung
- `error` Feld mit Fehlerbeschreibung

### Fallback-Strategie

Wenn der Slot-Pre-Check (Step 0) fehlschlägt (API-Error, Timeout):
1. Fallback zum alten Flow (ohne Pre-Check)
2. Lead wird erstellt
3. Wenn Slot nicht verfügbar → Lead existiert bereits (akzeptabler Trade-off)

---

## Best Practices

### 1. Slot-Verfügbarkeit vorab prüfen
Immer `GET /trial-offers/appointments/.../slots` aufrufen, bevor ein Lead erstellt wird. Verhindert "Datenmüll" bei nicht verfügbaren Slots.

### 2. Alternative Slots anbieten
Wenn gewünschter Slot nicht verfügbar:
```python
def _get_alternative_slots(target_datetime, slots, max_alternatives=3):
    """Findet die 3 nächsten Alternativen, sortiert nach Zeitabstand."""
```

### 3. Timezone-Handling
- Deutschland: `Europe/Berlin`
- Winter (CET): `+01:00`
- Sommer (CEST): `+02:00`
- Immer `pytz` für dynamische Timezone verwenden

### 4. Probetraining-Dauer
Standard-Dauer: **30 Minuten**
```python
duration_minutes = 30
end_datetime = start_datetime + timedelta(minutes=duration_minutes)
```

---

## Code-Referenzen

| Funktion | Datei | Beschreibung |
|----------|-------|--------------|
| `get_available_slots()` | `booking_service.py:127` | GET Slots Endpoint |
| `check_slot_availability()` | `booking_service.py:159` | Pre-Check mit Alternativen |
| `try_book_trial_offer()` | `booking_service.py:233` | Kompletter Trial Offer Flow |
| `try_book()` | `booking_service.py:196` | Bestandskunden-Buchung |
| `slot_unavailable_with_alternatives()` | `constants.py:61` | Deutsche Fehlermeldung |

---

## OpenAPI Dokumentation

Offizielle Dokumentation: https://developer.sportalliance.com/apis/magicline/openapi/

**Hinweis:** Die Dokumentationsseite verwendet JavaScript-Rendering. Für Details die Swagger/OpenAPI JSON direkt laden oder die obigen Endpoint-Beschreibungen verwenden.

---

*Letzte Aktualisierung: 2026-01-09*
