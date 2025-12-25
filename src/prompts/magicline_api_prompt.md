# Magicline Open API - Claude Code Prompt

Du bist ein Experte für die Magicline Open API. Nutze dieses Wissen, um Python-Code für die Integration mit der Magicline-Plattform zu schreiben.

## Überblick

Magicline ist Deutschlands größte cloudbasierte Studio-Management-Software für Fitnessstudios, Yoga-Studios, Physiotherapien und EMS-Studios. Die Open API folgt dem OpenAPI 3.0 Standard.

---

## Authentifizierung

```python
import requests

BASE_URL = "https://<tenant_name>.open-api.magicline.com/v1"
HEADERS = {
    "x-api-key": "<API_KEY>",
    "Content-Type": "application/json",
    "Accept-Language": "de"  # Optional: de, en, es, fr, it, nl, pl, etc.
}
```

**Wichtig:**
- Jedes Studio hat einen eigenen API-Key
- Der `tenant_name` wird bei der Aktivierung per E-Mail mitgeteilt
- Alle Requests müssen über HTTPS erfolgen

---

## Rate Limiting

- **Limit:** 1000 Requests pro Minute pro Endpoint
- **Bei Überschreitung:** HTTP 429 Response
- Jeder Endpoint hat seinen eigenen Request-Counter

---

## HTTP Status Codes

| Code | Bedeutung |
|------|-----------|
| 200 | Erfolg |
| 400 | Validierungsfehler - Request prüfen |
| 401 | Authentifizierung fehlgeschlagen - API-Key prüfen |
| 403 | Keine Berechtigung für diese Ressource |
| 404 | Ressource nicht gefunden |
| 429 | Rate Limit überschritten |
| 500 | Interner Serverfehler |

---

## Pagination (Data Chunking)

Die API unterstützt zwei Pagination-Varianten:

### Variante 1: ID-basiert
```python
# Erster Request
response = requests.get(f"{BASE_URL}/customers", headers=HEADERS)
data = response.json()

# Folge-Request mit offset
if data.get("hasNext"):
    next_response = requests.get(
        f"{BASE_URL}/customers?offset={data['offset']}", 
        headers=HEADERS
    )
```

### Variante 2: Index-basiert (mit sliceSize)
```python
params = {"sliceSize": 50, "offset": 0}
response = requests.get(f"{BASE_URL}/endpoint", headers=HEADERS, params=params)
```

**Response-Format:**
```json
{
  "result": [...],
  "offset": "1210206596",
  "hasNext": true
}
```

---

## API Scopes (Berechtigungen)

| Scope | Beschreibung |
|-------|--------------|
| `CUSTOMER_READ` | Kundendaten lesen |
| `CUSTOMER_WRITE` | Kundendaten schreiben |
| `CUSTOMER_CONTRACT_READ` | Verträge lesen |
| `CLASSES_READ` | Kurse lesen |
| `CLASSES_WRITE` | Kurse buchen/stornieren |
| `BOOKABLE_APPOINTMENTS_READ` | Buchbare Termine lesen |
| `APPOINTMENTS_READ` | Termine lesen |
| `APPOINTMENTS_WRITE` | Termine buchen/stornieren |
| `MEMBERSHIP_READ` | Mitgliedschaften lesen |
| `MEMBERSHIP_WRITE` | Mitgliedschaften schreiben |
| `MEMBERSHIP_SELF_SERVICE_READ` | Self-Service lesen |
| `MEMBERSHIP_SELF_SERVICE_WRITE` | Self-Service schreiben |
| `MEMBERSHIP_SELF_SERVICE_IDLE_PERIOD_READ` | Ruhezeiten lesen |
| `MEMBERSHIP_SELF_SERVICE_IDLE_PERIOD_WRITE` | Ruhezeiten schreiben |
| `CHECKIN_READ` | Check-ins lesen |
| `CHECKIN_WRITE` | Check-ins erstellen |
| `CHECKIN_VOUCHER_WRITE` | Check-in Gutscheine einlösen |
| `CUSTOMER_ACCOUNT_READ` | Kundenkonto lesen |
| `CUSTOMER_ACCOUNT_WRITE` | Kundenkonto schreiben |
| `CUSTOMER_SELF_SERVICE_READ` | Kunden-Self-Service lesen |
| `CUSTOMER_SELF_SERVICE_WRITE` | Kunden-Self-Service schreiben |
| `CUSTOMER_BENEFIT_READ` | Kundenvorteile lesen |
| `CUSTOMER_BENEFIT_WRITE` | Kundenvorteile schreiben |
| `COMMUNICATION_PREFERENCES_READ` | Kommunikationseinstellungen lesen |
| `COMMUNICATION_PREFERENCES_WRITE` | Kommunikationseinstellungen schreiben |
| `DEBT_COLLECTION_READ` | Inkasso lesen |
| `DEBT_COLLECTION_WRITE` | Inkasso schreiben |
| `EMPLOYEE_READ` | Mitarbeiter lesen |
| `DEVICE_READ` | Geräte lesen |
| `DEVICE_WRITE` | Geräte schreiben |
| `STUDIO_READ` | Studio-Infos lesen |
| `STUDIO_WRITE` | Studio-Infos schreiben |
| `TRIAL_OFFER_READ` | Probetraining lesen |
| `TRIAL_OFFER_WRITE` | Probetraining schreiben |
| `TAX_ADVISOR_EXPORT_READ` | Steuerberater-Export lesen |
| `PAYMENT_WRITE` | Zahlungen schreiben |

---

## Endpoints nach Kategorie

### 1. Customers (Kunden)

```python
# Alle Kunden abrufen (mit Pagination)
GET /v1/customers
GET /v1/customers?offset=0&sliceSize=50

# Einzelnen Kunden abrufen
GET /v1/customers/{customerId}

# Kunden nach Kriterien suchen
GET /v1/customers/by?email=example@email.com
GET /v1/customers/by?customerNumber=12345

# Kundensuche (POST)
POST /v1/customers/search
Body: {"firstName": "Max", "lastName": "Mustermann"}

# Check-in Historie eines Kunden
GET /v1/customers/{customerId}/activities/checkins

# Verträge eines Kunden
GET /v1/customers/{customerId}/contracts

# Alle Verträge abrufen
GET /v1/customers/contracts/by?contractStatus=ACTIVE

# Letzte Messdaten aller Kunden
GET /v1/customers/measurement/latest
```

**Python-Beispiel:**
```python
def get_all_customers():
    """Alle Kunden mit Pagination abrufen"""
    customers = []
    offset = "0"
    has_next = True
    
    while has_next:
        response = requests.get(
            f"{BASE_URL}/customers",
            headers=HEADERS,
            params={"offset": offset, "sliceSize": 50}
        )
        data = response.json()
        customers.extend(data.get("result", []))
        offset = data.get("offset", "0")
        has_next = data.get("hasNext", False)
    
    return customers

def search_customer(email: str):
    """Kunde per E-Mail suchen"""
    response = requests.get(
        f"{BASE_URL}/customers/by",
        headers=HEADERS,
        params={"email": email}
    )
    return response.json()
```

---

### 2. Customer Self-Service

```python
# Kontaktdaten abrufen
GET /v1/customers/{customerId}/self-service/contact-data

# Kontaktdaten ändern (erstellt Änderungsantrag)
POST /v1/customers/{customerId}/self-service/contact-data
Body: {
    "email": "neue-email@example.com",
    "phonePrivate": "+49 123456789",
    "phonePrivateMobile": "+49 987654321"
}

# Adressdaten abrufen
GET /v1/customers/{customerId}/self-service/address-data

# Adressdaten ändern
POST /v1/customers/{customerId}/self-service/address-data
Body: {
    "street": "Musterstraße",
    "houseNumber": "123",
    "zipCode": "12345",
    "city": "München",
    "countryCode": "DE"
}

# Stammdaten abrufen
GET /v1/customers/{customerId}/self-service/master-data

# Stammdaten ändern
POST /v1/customers/{customerId}/self-service/master-data
Body: {
    "firstName": "Max",
    "lastName": "Mustermann",
    "gender": "MALE",
    "dateOfBirth": "1990-01-15"
}

# Zahlungsdaten abrufen
GET /v1/customers/{customerId}/self-service/payment-data

# Zahlungsdaten ändern
POST /v1/customers/{customerId}/self-service/payment-data

# Änderungsantrag zurückziehen
DELETE /v1/customers/{customerId}/self-service/amendments/{amendmentId}
```

---

### 3. Customer Account (Kundenkonto)

```python
# Kontostand abrufen
GET /v1/customers/{customerId}/account/balances
# Response: accountBalance, consumptionCredit, dunningLevel, inDebtCollection

# Vergangene Transaktionen
GET /v1/customers/{customerId}/account/transactions?offset=0&sliceSize=10

# Zukünftige Transaktionen (nächstes Jahr)
GET /v1/customers/{customerId}/account/transactions/upcoming?offset=0&sliceSize=10
```

**Python-Beispiel:**
```python
def get_customer_balance(customer_id: int):
    """Kontostand eines Kunden abrufen"""
    response = requests.get(
        f"{BASE_URL}/customers/{customer_id}/account/balances",
        headers=HEADERS
    )
    return response.json()
    # Returns: {"accountBalance": {"amount": 20, "currency": "EUR"}, ...}
```

---

### 4. Classes (Kurse)

```python
# Alle Kurse abrufen
GET /v1/classes
GET /v1/classes?from=2024-01-01&to=2024-12-31

# Einzelnen Kurs abrufen
GET /v1/classes/{classId}

# Alle buchbaren Kurs-Slots
GET /v1/classes/slots
GET /v1/classes/slots?from=2024-01-01T00:00:00&to=2024-01-31T23:59:59

# Slots eines bestimmten Kurses
GET /v1/classes/{classId}/slots

# Einzelnen Slot abrufen
GET /v1/classes/{classId}/slots/{classSlotId}

# Buchung validieren (vor dem Buchen!)
POST /v1/classes/booking/validate
Body: {
    "customerId": 12345,
    "classSlotId": 67890
}

# Kurs buchen
POST /v1/classes/booking/book
Body: {
    "customerId": 12345,
    "classSlotId": 67890
}

# Buchung abrufen
GET /v1/classes/booking/{bookingId}

# Buchung stornieren
DELETE /v1/classes/booking/{bookingId}

# Alle Buchungen eines Kunden
GET /v1/classes/booking?customerId=12345
```

**Python-Beispiel:**
```python
def book_class(customer_id: int, class_slot_id: int):
    """Kurs für einen Kunden buchen"""
    # Erst validieren
    validate_response = requests.post(
        f"{BASE_URL}/classes/booking/validate",
        headers=HEADERS,
        json={"customerId": customer_id, "classSlotId": class_slot_id}
    )
    
    if validate_response.status_code != 200:
        return {"error": "Validierung fehlgeschlagen", "details": validate_response.json()}
    
    # Dann buchen
    book_response = requests.post(
        f"{BASE_URL}/classes/booking/book",
        headers=HEADERS,
        json={"customerId": customer_id, "classSlotId": class_slot_id}
    )
    
    return book_response.json()
```

---

### 5. Appointments (Termine)

```python
# Alle buchbaren Termintypen
GET /v1/appointments/bookable

# Details eines Termintyps
GET /v1/appointments/bookable/{bookableAppointmentId}

# Verfügbare Slots für einen Termintyp
GET /v1/appointments/bookable/{bookableAppointmentId}/slots
GET /v1/appointments/bookable/{id}/slots?from=2024-01-01T08:00:00&to=2024-01-01T18:00:00

# Terminbuchung validieren
POST /v1/appointments/bookable/validate
Body: {
    "customerId": 12345,
    "bookableAppointmentId": 111,
    "slotStart": "2024-01-15T10:00:00",
    "slotEnd": "2024-01-15T11:00:00"
}

# Termin buchen
POST /v1/appointments/booking/book
Body: {
    "customerId": 12345,
    "bookableAppointmentId": 111,
    "slotStart": "2024-01-15T10:00:00",
    "slotEnd": "2024-01-15T11:00:00"
}

# Buchung abrufen
GET /v1/appointments/booking/{bookingId}

# Buchung stornieren
DELETE /v1/appointments/booking/{bookingId}

# Alle Terminbuchungen eines Kunden
GET /v1/appointments/booking?customerId=12345
```

---

### 6. Memberships (Mitgliedschaften)

```python
# Alle verfügbaren Mitgliedschafts-Angebote
GET /v1/memberships/membership-offers

# Details eines Angebots
GET /v1/memberships/membership-offers/{membershipOfferId}

# Signup-Vorschau (zeigt Preise, Laufzeit etc.)
POST /v1/memberships/signup/preview
Body: {
    "contract": {
        "contractOfferTermId": 1000,
        "startDate": "2024-02-01",
        "preuseDate": "2024-01-15"
    },
    "customer": {
        "firstName": "Max",
        "lastName": "Mustermann",
        "email": "max@example.com",
        "dateOfBirth": "1990-01-15",
        "gender": "MALE",
        "street": "Musterstraße",
        "houseNumber": "1",
        "zipCode": "12345",
        "city": "München",
        "countryCode": "DE"
    }
}

# Neuen Kunden mit Mitgliedschaft anmelden
POST /v1/memberships/signup
Body: { /* wie preview, mit zusätzlichen Feldern */ }

# Mitgliedschaft zu bestehendem Kunden hinzufügen (Vorschau)
POST /v1/memberships/customers/{customerId}/add-membership/preview
Body: {
    "contractOfferTermId": 1000,
    "startDate": "2024-02-01"
}

# Mitgliedschaft zu bestehendem Kunden hinzufügen
POST /v1/memberships/customers/{customerId}/add-membership

# Tarifwechsel-Konfigurationen
GET /v1/memberships/{customerId}/membership-switch/configs
GET /v1/memberships/{customerId}/membership-switch/configs/{configId}

# Tarifwechsel durchführen
POST /v1/memberships/{customerId}/membership-switch
```

---

### 7. Membership Self-Service

```python
# Vertragsdaten abrufen
GET /v1/memberships/{customerId}/self-service/contract-data

# Ordentliche Kündigung einreichen
POST /v1/memberships/{customerId}/self-service/ordinary-contract-cancelation
Body: {
    "contractId": 12345,
    "reasonId": 1,
    "notes": "Umzug in andere Stadt"
}

# Kündigungsgründe abrufen
GET /v1/memberships/self-service/contract-cancelation-reasons

# Kündigung zurückziehen
POST /v1/memberships/{customerId}/self-service/withdraw-ordinary-contract-cancelation/{contractId}

# Ruhezeiten-Konfiguration
GET /v1/memberships/{contractId}/self-service/idle-periods/config

# Ruhezeit validieren
POST /v1/memberships/{contractId}/self-service/idle-periods/validate
Body: {
    "startDate": "2024-06-01",
    "temporalUnit": "MONTH",
    "termValue": 1,
    "reasonId": 1
}

# Ruhezeiten abrufen
GET /v1/memberships/{contractId}/self-service/idle-periods

# Ruhezeit anlegen (multipart/form-data)
POST /v1/memberships/{contractId}/self-service/idle-periods
# Siehe Abschnitt "Multipart Requests"

# Ruhezeit stornieren
DELETE /v1/memberships/{contractId}/self-service/idle-periods/{idlePeriodId}

# Zusatzmodule abrufen
GET /v1/memberships/{customerId}/self-service/additional-modules
GET /v1/memberships/{customerId}/self-service/additional-modules/{moduleId}

# Zusatzmodul buchen
POST /v1/memberships/{customerId}/self-service/additional-modules
Body: {
    "additionalModuleId": 123,
    "contractId": 456,
    "startDate": "2024-02-01"
}

# Zusatzmodul kündigen
DELETE /v1/memberships/{customerId}/self-service/additional-modules/{moduleContractId}
```

---

### 8. Check-ins

```python
# Check-in Gutschein einlösen
POST /v1/checkin-vouchers/redeem
Body: {
    "voucherCode": "CHVB1-YL29-MYVA",
    "firstname": "Max",
    "lastname": "Mustermann",
    "email": "max@example.com"
}
```

---

### 9. Cross-Studio (Studio-übergreifend)

```python
# Kunden studio-übergreifend suchen
GET /v1/cross-studio/customers/by?email=max@example.com
GET /v1/cross-studio/customers/{customerId}
POST /v1/cross-studio/customers/search

# Check-in Aktivitäten studio-übergreifend
GET /v1/cross-studio/customers/{customerId}/activities/checkins

# Studios mit Mitgliedschaftsangeboten
GET /v1/cross-studio/membership-offers/studios
```

---

### 10. Studios

```python
# Studio-Informationen
GET /v1/studios/information

# Aktuelle Auslastung
GET /v1/studios/utilization

# Aktivierung bestätigen
POST /v1/studios/confirmActivation
```

---

### 11. Employees (Mitarbeiter)

```python
# Alle Mitarbeiter
GET /v1/employees

# Einzelner Mitarbeiter
GET /v1/employees/{employeeId}
```

---

### 12. Devices (Geräte)

```python
# Alle Geräte
GET /v1/devices

# Gerät aktivieren
PUT /v1/devices/{deviceId}/activate
```

---

### 13. Finance / Debt Collection (Inkasso)

```python
# Inkasso-Konfiguration
GET /v1/debt-collection/configuration

# Schuldner eines Inkassolaufs
GET /v1/debt-collection/{debtCollectionRunId}/debtors

# Details eines Inkassolaufs
GET /v1/debt-collection/{debtCollectionRunId}/details

# Inkasso aktualisieren
POST /v1/debt-collection/update
Body: {
    "debtors": [{
        "debtorId": "debtor-123",
        "agencyCollectionCases": [{
            "agencyCollectionCaseId": "case-456",
            "collectionCaseIds": ["ml-case-1", "ml-case-2"],
            "debts": [{
                "debtId": "debt-1",
                "originalAmount": 100,
                "paidAmount": 50,
                "canceledAmount": 0,
                "currency": "EUR"
            }]
        }]
    }],
    "requestId": "unique-request-id"
}

# Transfer bestätigen
POST /v1/debt-collection/{debtCollectionRunId}/confirmTransfer

# Inkasso-Fälle
GET /v1/debt-collection/cases

# Gesperrte Schuldner
GET /v1/debt-collection/blocked/debtors

# Gesperrte Schulden
GET /v1/debt-collection/blocked/debts
```

---

### 14. Trial Offers (Probetraining)

```python
# Buchbare Probetrainings (Kurse)
GET /v1/trial-offers/bookable-trial-offers/classes

# Buchbare Probetrainings (Termine)
GET /v1/trial-offers/bookable-trial-offers/appointments/bookable

# Konfiguration
GET /v1/trial-offers/config/{configId}

# Lead validieren
POST /v1/trial-offers/lead/validate
Body: {
    "firstName": "Max",
    "lastName": "Mustermann",
    "email": "max@example.com"
}

# Lead erstellen
POST /v1/trial-offers/lead/create

# Kurs-Slots für Probetraining
GET /v1/trial-offers/bookable-trial-offers/classes/{classId}/slots

# Termin-Slots für Probetraining
GET /v1/trial-offers/bookable-trial-offers/appointments/bookable/{bookableAppointmentId}/slots

# Kurs-Buchung validieren
POST /v1/trial-offers/classes/booking/validate

# Kurs buchen
POST /v1/trial-offers/classes/booking/book

# Termin-Buchung validieren
POST /v1/trial-offers/appointments/booking/validate

# Termin buchen
POST /v1/trial-offers/appointments/booking/book
```

---

### 15. Customer Communication

```python
# Neuen Thread erstellen
POST /v1/communications/{customerId}/threads
Body: {
    "subject": "Betreff",
    "message": "Nachricht"
}

# Thread aktualisieren
PUT /v1/communications/{customerId}/threads/{threadId}

# Kommunikationseinstellungen abrufen
GET /v1/communications/{customerId}/communication-preferences

# Kommunikationseinstellungen ändern
PUT /v1/communications/{customerId}/communication-preferences
Body: {
    "emailAllowed": true,
    "smsAllowed": false,
    "phoneAllowed": true
}
```

---

### 16. Tax Advisor Export (Steuerberater)

```python
# Export-Daten abrufen (nach Webhook-Event)
GET /v1/tax-advisor/exports/{exportId}
```

---

### 17. Payments

```python
# User-Session für Zahlung erstellen
POST /v1/payments/user-session
```

---

## Multipart/Form-Data Requests

Einige Endpoints erfordern multipart/form-data (z.B. für Datei-Uploads):

```python
import requests

def create_idle_period_with_document(contract_id: int, data: dict, document_path: str):
    """Ruhezeit mit Dokument anlegen"""
    
    files = {
        'data': (None, json.dumps(data), 'application/json'),
        'document': ('document.pdf', open(document_path, 'rb'), 'application/pdf')
    }
    
    headers = {"x-api-key": API_KEY}  # Kein Content-Type Header bei multipart!
    
    response = requests.post(
        f"{BASE_URL}/memberships/{contract_id}/self-service/idle-periods",
        headers=headers,
        files=files
    )
    return response.json()

# Beispiel-Aufruf
data = {
    "startDate": "2024-06-01",
    "temporalUnit": "MONTH",
    "termValue": 1,
    "reasonId": 1
}
result = create_idle_period_with_document(12345, data, "/path/to/document.pdf")
```

---

## Webhooks

Webhooks senden nur Benachrichtigungen - Details müssen via API abgerufen werden.

### Webhook-Format
```json
{
    "entityId": 7893459,
    "uuid": "095be615-a8ad-4c33-8e9c-c7612fbf6c9f",
    "payload": [{
        "timestamp": 1642779144176,
        "type": "CUSTOMER_CREATED",
        "content": {}
    }]
}
```

### Event-Types

| Event | entityId | Beschreibung |
|-------|----------|--------------|
| `CUSTOMER_CREATED` | customerId | Neuer Kunde erstellt |
| `CUSTOMER_UPDATED` | customerId | Kundendaten geändert |
| `CUSTOMER_DELETED` | customerId | Kunde gelöscht |
| `CUSTOMER_CHECKIN` | customerId | Kunde eingecheckt |
| `CUSTOMER_CHECKOUT` | customerId | Kunde ausgecheckt |
| `CUSTOMER_ACCESS_DISABLED` | customerId | Kundenzugang deaktiviert |
| `CUSTOMER_HOME_STUDIO_UPDATED` | customerId | Heimstudio geändert (content: sourceStudioId, targetStudioId) |
| `CONTRACT_CREATED` | customerId | Vertrag erstellt (content: contractId) |
| `CONTRACT_UPDATED` | customerId | Vertrag geändert (content: contractId) |
| `CONTRACT_CANCELLED` | customerId | Vertrag gekündigt (content: contractId) |
| `CONTRACT_IDLE_PERIOD_CREATED` | customerId | Ruhezeit erstellt (content: contractId, idlePeriodId) |
| `CONTRACT_IDLE_PERIOD_UPDATED` | customerId | Ruhezeit geändert |
| `CONTRACT_IDLE_PERIOD_CANCELLED` | customerId | Ruhezeit storniert |
| `CONTRACT_ADDITIONAL_MODULE_CREATED` | customerId | Zusatzmodul erstellt |
| `CONTRACT_ADDITIONAL_MODULE_UPDATED` | customerId | Zusatzmodul geändert |
| `CONTRACT_ADDITIONAL_MODULE_CANCELLED` | customerId | Zusatzmodul gekündigt |
| `CLASS_BOOKING_CREATED` | bookingId | Kursbuchung erstellt |
| `CLASS_BOOKING_UPDATED` | bookingId | Kursbuchung geändert |
| `CLASS_BOOKING_CANCELLED` | bookingId | Kursbuchung storniert |
| `CLASS_SLOT_UPDATED` | classSlotId | Kurs-Slot geändert (content: classId) |
| `CLASS_SLOT_CANCELLED` | classSlotId | Kurs-Slot abgesagt |
| `APPOINTMENT_BOOKING_CREATED` | bookingId | Terminbuchung erstellt |
| `APPOINTMENT_BOOKING_UPDATED` | bookingId | Terminbuchung geändert |
| `APPOINTMENT_BOOKING_CANCELLED` | bookingId | Terminbuchung storniert |
| `EMPLOYEE_CREATED` | employeeId | Mitarbeiter erstellt |
| `EMPLOYEE_UPDATED` | employeeId | Mitarbeiter geändert |
| `EMPLOYEE_DELETED` | employeeId | Mitarbeiter gelöscht |
| `DEVICE_CREATED` | deviceId | Gerät erstellt |
| `FINANCE_DEBT_COLLECTION_RUN_CREATED` | debtCollectionRunId | Inkassolauf erstellt |
| `FINANCE_DEBT_COLLECTION_CASE_UPDATED` | caseAdjustmentRequestId | Inkassofall aktualisiert |
| `STUDIO_OPENING_HOURS_UPDATED` | studioId | Öffnungszeiten geändert |
| `TAX_ADVISOR_EXPORT_CREATED` | exportId | Steuerberater-Export erstellt |
| `AGGREGATOR_MEMBER_CREATED` | customerId | Aggregator-Mitglied erstellt |
| `CUSTOMER_ACCESS_MEDIUM_CREATED` | customerId | Zugangsmedium erstellt |
| `CUSTOMER_ACCESS_MEDIUM_UPDATED` | customerId | Zugangsmedium geändert |
| `CUSTOMER_ACCESS_MEDIUM_DELETED` | customerId | Zugangsmedium gelöscht |
| `CUSTOMER_ACCESS_RESTRICTION_CREATED` | customerId | Zugangsbeschränkung erstellt |
| `CUSTOMER_ACCESS_RESTRICTION_DELETED` | customerId | Zugangsbeschränkung entfernt |
| `AUTOMATIC_CUSTOMER_CHECKOUT` | studioId | Automatischer Checkout (content: checkouts[]) |

### Webhook-Handler (Flask-Beispiel)
```python
from flask import Flask, request, jsonify

app = Flask(__name__)

WEBHOOK_API_KEY = "your-webhook-api-key"

@app.route('/webhook', methods=['POST'])
def handle_webhook():
    # API-Key validieren
    if request.headers.get('x-api-key') != WEBHOOK_API_KEY:
        return jsonify({"error": "Unauthorized"}), 401
    
    data = request.json
    entity_id = data.get('entityId')
    event_type = data['payload'][0]['type']
    timestamp = data['payload'][0]['timestamp']
    
    # Event verarbeiten
    if event_type == 'CUSTOMER_CREATED':
        # Kundendaten via API abrufen (NICHT während Webhook-Verarbeitung!)
        # Stattdessen: In Queue speichern und asynchron verarbeiten
        queue.add({'type': 'fetch_customer', 'customer_id': entity_id})
    
    elif event_type == 'CLASS_BOOKING_CREATED':
        queue.add({'type': 'sync_booking', 'booking_id': entity_id})
    
    # Webhook bestätigen (innerhalb von 5000ms!)
    return jsonify({"status": "received"}), 200
```

**Wichtig:**
- Response innerhalb von 5000ms
- Bei Fehler: 3 Wiederholungsversuche nach je 10 Minuten
- NICHT die Open API während der Webhook-Verarbeitung aufrufen!
- Webhooks asynchron verarbeiten

---

## Vollständiges Python-Client-Beispiel

```python
import requests
from typing import Optional, List, Dict, Any
from dataclasses import dataclass
from datetime import date, datetime

@dataclass
class MagiclineConfig:
    tenant_name: str
    api_key: str
    language: str = "de"

class MagiclineClient:
    def __init__(self, config: MagiclineConfig):
        self.base_url = f"https://{config.tenant_name}.open-api.magicline.com/v1"
        self.headers = {
            "x-api-key": config.api_key,
            "Content-Type": "application/json",
            "Accept-Language": config.language
        }
    
    def _get(self, endpoint: str, params: Optional[Dict] = None) -> Dict[str, Any]:
        response = requests.get(
            f"{self.base_url}{endpoint}",
            headers=self.headers,
            params=params
        )
        response.raise_for_status()
        return response.json()
    
    def _post(self, endpoint: str, data: Dict[str, Any]) -> Dict[str, Any]:
        response = requests.post(
            f"{self.base_url}{endpoint}",
            headers=self.headers,
            json=data
        )
        response.raise_for_status()
        return response.json()
    
    def _delete(self, endpoint: str) -> Dict[str, Any]:
        response = requests.delete(
            f"{self.base_url}{endpoint}",
            headers=self.headers
        )
        response.raise_for_status()
        return response.json()
    
    # === CUSTOMERS ===
    
    def get_customers(self, slice_size: int = 50) -> List[Dict]:
        """Alle Kunden mit Pagination abrufen"""
        customers = []
        offset = "0"
        has_next = True
        
        while has_next:
            data = self._get("/customers", {"offset": offset, "sliceSize": slice_size})
            customers.extend(data.get("result", []))
            offset = data.get("offset", "0")
            has_next = data.get("hasNext", False)
        
        return customers
    
    def get_customer(self, customer_id: int) -> Dict:
        return self._get(f"/customers/{customer_id}")
    
    def search_customer_by_email(self, email: str) -> Optional[Dict]:
        return self._get("/customers/by", {"email": email})
    
    def get_customer_contracts(self, customer_id: int) -> List[Dict]:
        return self._get(f"/customers/{customer_id}/contracts")
    
    def get_customer_checkins(self, customer_id: int) -> List[Dict]:
        return self._get(f"/customers/{customer_id}/activities/checkins")
    
    def get_customer_balance(self, customer_id: int) -> Dict:
        return self._get(f"/customers/{customer_id}/account/balances")
    
    # === CLASSES ===
    
    def get_classes(self, from_date: Optional[date] = None, to_date: Optional[date] = None) -> List[Dict]:
        params = {}
        if from_date:
            params["from"] = from_date.isoformat()
        if to_date:
            params["to"] = to_date.isoformat()
        return self._get("/classes", params)
    
    def get_class_slots(self, class_id: int) -> List[Dict]:
        return self._get(f"/classes/{class_id}/slots")
    
    def validate_class_booking(self, customer_id: int, class_slot_id: int) -> Dict:
        return self._post("/classes/booking/validate", {
            "customerId": customer_id,
            "classSlotId": class_slot_id
        })
    
    def book_class(self, customer_id: int, class_slot_id: int) -> Dict:
        return self._post("/classes/booking/book", {
            "customerId": customer_id,
            "classSlotId": class_slot_id
        })
    
    def cancel_class_booking(self, booking_id: int) -> Dict:
        return self._delete(f"/classes/booking/{booking_id}")
    
    # === APPOINTMENTS ===
    
    def get_bookable_appointments(self) -> List[Dict]:
        return self._get("/appointments/bookable")
    
    def get_appointment_slots(self, bookable_appointment_id: int, 
                               from_dt: Optional[datetime] = None,
                               to_dt: Optional[datetime] = None) -> List[Dict]:
        params = {}
        if from_dt:
            params["from"] = from_dt.isoformat()
        if to_dt:
            params["to"] = to_dt.isoformat()
        return self._get(f"/appointments/bookable/{bookable_appointment_id}/slots", params)
    
    def book_appointment(self, customer_id: int, bookable_appointment_id: int,
                         slot_start: datetime, slot_end: datetime) -> Dict:
        return self._post("/appointments/booking/book", {
            "customerId": customer_id,
            "bookableAppointmentId": bookable_appointment_id,
            "slotStart": slot_start.isoformat(),
            "slotEnd": slot_end.isoformat()
        })
    
    def cancel_appointment(self, booking_id: int) -> Dict:
        return self._delete(f"/appointments/booking/{booking_id}")
    
    # === MEMBERSHIPS ===
    
    def get_membership_offers(self) -> List[Dict]:
        return self._get("/memberships/membership-offers")
    
    def signup_preview(self, contract_data: Dict, customer_data: Dict) -> Dict:
        return self._post("/memberships/signup/preview", {
            "contract": contract_data,
            "customer": customer_data
        })
    
    def signup(self, contract_data: Dict, customer_data: Dict) -> Dict:
        return self._post("/memberships/signup", {
            "contract": contract_data,
            "customer": customer_data
        })
    
    # === STUDIO ===
    
    def get_studio_info(self) -> Dict:
        return self._get("/studios/information")
    
    def get_studio_utilization(self) -> Dict:
        return self._get("/studios/utilization")
    
    # === EMPLOYEES ===
    
    def get_employees(self) -> List[Dict]:
        return self._get("/employees")


# Verwendung
if __name__ == "__main__":
    config = MagiclineConfig(
        tenant_name="dein-tenant",
        api_key="dein-api-key"
    )
    
    client = MagiclineClient(config)
    
    # Beispiele
    customers = client.get_customers()
    print(f"Anzahl Kunden: {len(customers)}")
    
    classes = client.get_classes()
    print(f"Anzahl Kurse: {len(classes)}")
    
    studio = client.get_studio_info()
    print(f"Studio: {studio.get('name')}")
```

---

## Wichtige Hinweise

1. **Immer HTTPS verwenden**
2. **Rate Limits beachten** (1000 req/min pro Endpoint)
3. **Pagination bei Listen verwenden** (hasNext/offset)
4. **Vor Buchungen immer validieren** (validate-Endpoints)
5. **Webhooks asynchron verarbeiten** (max 5000ms Response-Zeit)
6. **API-Keys sicher speichern** (Umgebungsvariablen)
7. **Bilder-URLs haben Ablaufzeit** (2 Stunden)

---

## Demo-Server

Für Tests steht ein Demo-Server zur Verfügung:
```
https://open-api-demo.open-api.magicline.com/v1
```

---

## Weiterführende Links

- Developer Portal: https://developer.sportalliance.com/
- OpenAPI Spec Download: https://developer.sportalliance.com/_bundle/apis/magicline/openapi/openapi.json
- Webhooks: https://developer.sportalliance.com/apis/magicline/webhooks/general-information
