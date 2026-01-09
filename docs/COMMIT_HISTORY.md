# Commit History - EasyFitness Chatbot

Chronologische Zusammenfassung aller relevanten Commits für die nächste Session.

---

## Übersicht nach Phasen

| Phase | Zeitraum | Fokus |
|-------|----------|-------|
| **Phase 1** | 25.12.2025 - 29.12.2025 | Grundlegende Struktur, Tests, MagicLine Integration |
| **Phase 2** | 03.01.2026 - 05.01.2026 | Test-Infrastruktur, Import-Fixes |
| **Phase 3** | 05.01.2026 - 06.01.2026 | Kritische Booking-Flow Bugfixes |
| **Phase 4** | 06.01.2026 - 07.01.2026 | LLM-Kontext, Trial Offer Robustheit |
| **Phase 5** | 08.01.2026 | Date Extraction Bug, 1-Satz Responses, Prompt-Optimierung |
| **Phase 6** | 09.01.2026 | Slot Availability Pre-Check (aktuelle Session) |

---

## Phase 1: Grundlagen (25.12 - 29.12.2025)

### `54d560e` - MagicLine Trial Offer Config
**Datum:** 29.12.2025

**Änderungen:**
- `MAGICLINE_TRIAL_OFFER_CONFIG_ID` Environment Variable hinzugefügt
- Ermöglicht Trial Offer Buchungen über MagicLine OpenAPI

---

### `4b203a7` - ExtractionService Rewrite
**Datum:** 29.12.2025

**Änderungen:**
- ExtractionService komplett neu geschrieben
- LLM-basierte Extraktion für `vorname`, `nachname`, `email`
- Ersetzt regelbasierte Extraktion durch intelligentere LLM-Variante

---

### `33fb457` - Testcases hinzugefügt
**Datum:** 29.12.2025

**Änderungen:**
- Erste Testfälle von Claude Code generiert
- Grundlegende Unit-Tests für Services

---

## Phase 2: Test-Infrastruktur (03.01 - 05.01.2026)

### `827942e` - Import Fixes in Tests
**Datum:** 03.01.2026

**Problem:** Tests schlugen fehl wegen falscher Import-Pfade
**Lösung:** Import-Struktur in Test-Dateien korrigiert

---

### `3e12b60` - Test Environment Variables
**Datum:** 03.01.2026

**Problem:** `config.py` lädt `.env` sofort beim Import → Tests verwenden Produktions-Werte
**Lösung:**
```python
# WICHTIG: Test-Environment-Variables VOR allen anderen Imports setzen
# Muss auf Modul-Ebene passieren, bevor pytest fixtures laufen
```

---

### `8b47ca0` - Fix Test Infrastructure
**Datum:** 05.01.2026

**Änderungen:**
- 4 fehlerhafte Tests repariert
- Test-Infrastruktur stabilisiert
- Fixtures für temporäre Dateien hinzugefügt

---

## Phase 3: Kritische Booking-Flow Fixes (05.01 - 06.01.2026)

### `676becd` - Hybrid Extraction + Multi-Format Parsing
**Datum:** 06.01.2026

**Kritisches Problem:** Booking-Flow funktionierte nicht

**Root Causes:**
1. LLM-Extraktion unzuverlässig (falsche Daten, fehlende Zeit)
2. Booking Intent nicht erkannt bei Multi-Message-Flow
3. LLM gab Python-Dict statt JSON zurück (`{'reply': '...'}`)

**Lösungen:**
- **Hybrid Extraction:** LLM + Regex-Fallback für Datum/Zeit
- **Multi-Format Parsing:** JSON, Python-Dict, ast.literal_eval
- **Context-Aware Booking Intent:** Berücksichtigt gespeicherte Daten

**Betroffene Dateien:**
- `src/constants.py` (NEU) - Zentralisierte Konstanten
- `src/api/routes.py` - Hybrid Extraction
- `src/services/chat_service.py` - Multi-Format Parsing
- `src/services/extraction_service.py` - Verbesserte Prompts
- `src/utils/text_parser.py` - Context-Aware Intent Detection

---

### `3baee96` - Known Limitations Fix
**Datum:** 06.01.2026

**Behobene Limitierungen:**
1. ~~LLM extraction unreliable~~ → `generate_extraction()` mit temperature=0.1
2. ~~Attention mask warning~~ → Proper pad_token Konfiguration
3. ~~No booking confirmation persistence~~ → `bookings` Liste mit History

---

### `d51e1b6` - Live Test Failures Fix
**Datum:** 06.01.2026

**Probleme aus Live-Test:**
1. Date "am 9.1" Format nicht erkannt
2. Name aus "Name, email" Format nicht extrahiert
3. Regex kam nach LLM (falsches Datum überschrieb korrektes)

**Lösungen:**
- `extract_date_only()` erweitert für "am 9.1" Format
- `extract_full_name()` Funktion hinzugefügt
- **WICHTIG: Regex ZUERST, dann LLM-Fallback**

---

### `b9aa116` - Critical Bugs from Code Review
**Datum:** 06.01.2026

**Fixes:**
- Booking Auto-Trigger wenn alle Daten komplett
- Profile Data Persistence Strategy (5-Schritt)
- KeyError-Safety mit `.get()` statt direktem Zugriff

---

### `3c64cfe` - Time Validation
**Datum:** 06.01.2026

**Änderung:**
- `extract_time_only()` validiert jetzt Uhrzeiten
- Verhindert ungültige Zeiten wie "25:00" oder "12:99"

---

## Phase 4: LLM-Kontext & Trial Offer (06.01 - 07.01.2026)

### `9e84516` - Booking Status Context für LLM
**Datum:** 06.01.2026

**Problem:** Bot fragte nach Daten, die er schon hatte

**Lösung:** `[BUCHUNGSSTATUS]` im System Prompt:
```json
{
  "ist_bestandskunde": false,
  "vorname": "Max",
  "nachname": null,
  "email": "max@test.de",
  "datum": "2026-01-15",
  "uhrzeit": null
}
```

**Regeln für LLM:**
- `null` → danach fragen (EINE Frage pro Nachricht)
- Hat Wert → NICHT nochmal fragen
- `ist_bestandskunde: true` → nur datum/uhrzeit nötig

---

### `d2468f8` - Data Loss Bugs Fix
**Datum:** 06.01.2026

**Problem:** Extrahierte Daten gingen verloren zwischen Messages

**Lösung:**
- Profile-Update mit Merge-Strategie
- Neue Daten überschreiben nur wenn nicht-null
- Alte Daten bleiben erhalten

---

### `4e59fda` - Trial Offer Robustness
**Datum:** 07.01.2026

**Verbesserungen:**
- Bessere Error-Handling in `try_book_trial_offer()`
- Fallback bei API-Fehlern
- Detailliertere Fehlermeldungen

---

## Phase 5: Date Bug & Prompt-Optimierung (08.01.2026)

### `e2d0b22` - Date Extraction Bug + 1-Satz Responses
**Datum:** 08.01.2026

**Problem 1:** Nach Booking-Failure wurde falsches Datum angezeigt
- Chat LLM extrahierte Datum aus History
- Überschrieb das bereits gelöschte Datum

**Lösung:**
```python
# KRITISCH: datum/uhrzeit ausschließen - Chat LLM extrahiert diese aus History
excluded_fields = {"datum", "uhrzeit"}
```

**Problem 2:** Bot gab 2-4 Sätze statt 1

**Lösung:** Prompt geändert:
- "Maximal 2-3 kurze Sätze" → "MAXIMAL EIN SATZ pro Nachricht (STRIKT!)"

---

### `2135e98` - Prompt-Struktur Optimierung
**Datum:** 08.01.2026

**Änderungen am Prompt:**

| Aspekt | Alt | Neu |
|--------|-----|-----|
| Begrüßung | Keine Beispiele | Klare Beispiele für "Hallo", "Hi" |
| Verkaufsfokus | "Lenke JEDES Gespräch dahin" | Phasen-Modell (erst kennenlernen) |
| Redundanzen | 3x "eine Frage pro Nachricht" | 1x in [GESPRÄCHSSTIL] |
| Struktur | Buchungsregeln vor Verhalten | Logischer Flow |
| Verboten | 3 Regeln | 4 Regeln (+Nicht sofort verkaufen) |

---

### `aac9b1f` - Lead Skeleton Fix
**Datum:** 08.01.2026

**Änderungen:**
- Lead Creation Skeleton korrigiert
- Lead Validation Skeleton korrigiert
- UI Tabs hinzugefügt

---

## Phase 6: Slot Availability Pre-Check (09.01.2026 - Aktuelle Session)

### Noch nicht committet - Aktuelle Änderungen

**Problem:** Lead wird erstellt BEVOR geprüft wird, ob Slot verfügbar ist
→ "Datenmüll" in MagicLine wenn Slot belegt

**Lösung:** Pre-Check VOR Lead-Erstellung

**Neuer Flow:**
```
0. GET /trial-offers/appointments/.../slots  ← NEU
1. POST /trial-offers/lead/validate
2. POST /trial-offers/lead/create
3. POST /appointments/bookable/validate
4. POST /appointments/booking/book
```

**Neue Methoden in `booking_service.py`:**
- `get_available_slots()` - GET Endpoint
- `check_slot_availability()` - Pre-Check mit Alternativen
- `_get_alternative_slots()` - Findet nächste verfügbare Zeiten
- `_parse_slot_datetime()` - Datetime-Parsing
- `_format_time_from_datetime()` - Zeit-Formatierung
- `_calculate_time_distance()` - Zeitabstand berechnen
- `_is_same_date()` - Datumsvergleich
- `_extract_date_from_datetime()` - Datum extrahieren

**Neue Konstante in `constants.py`:**
```python
@staticmethod
def slot_unavailable_with_alternatives(alternatives: list[str]) -> str:
    # "Diese Zeit ist leider belegt. Verfügbar wäre: 10:00 Uhr, 11:00 Uhr oder 14:00 Uhr."
```

**Neue Test-Fixtures in `magicline_responses.py`:**
- `SLOTS_AVAILABLE` - 6 Standard-Slots
- `SLOTS_EMPTY` - Leeres Array
- `create_slots_response()` - Konfigurierbarer Response

**Neue Tests:**
- 33+ Tests in `test_booking_service.py`
- 5 Tests in `test_session_changes.py`
- Updates in `test_booking_flow.py`

**Teststand:** 354 Tests passing (war 321)

---

## Wichtige Code-Patterns

### 1. Extraction Priority (routes.py)
```python
# REGEX ZUERST (zuverlässiger), dann LLM für komplexe Fälle
new_date = extract_date_only(text)  # Regex
if not new_date:
    new_date = extracted_data.get("datum")  # LLM Fallback
```

### 2. Multi-Format Response Parsing (chat_service.py)
```python
# Try 1: Standard JSON
data = json.loads(json_str)
# Try 2: Python dict syntax
fixed_str = json_str.replace("'", '"').replace("None", "null")
# Try 3: ast.literal_eval
data = ast.literal_eval(json_str)
```

### 3. Date Field Exclusion (routes.py)
```python
# Chat LLM darf datum/uhrzeit NICHT überschreiben
excluded_fields = {"datum", "uhrzeit"}
```

### 4. Slot Pre-Check mit Fallback (booking_service.py)
```python
slot_check = self.check_slot_availability(start_datetime)
if not slot_check.get("api_error"):  # Pre-check erfolgreich
    if not slot_check.get("available"):
        return False, BotMessages.slot_unavailable_with_alternatives(alternatives), None
# Bei API-Error: Fallback zum alten Flow
```

---

## Bekannte Einschränkungen

1. **Nur Deutsch:** Alle Prompts und Parsing auf Deutsch
2. **Lokales LLM:** Kein Cloud-LLM, läuft auf GPU (7.6GB VRAM)
3. **JSON-Persistenz:** Kein Database, alles in `customers.json`
4. **30-Min Slots:** Probetraining ist fix 30 Minuten

---

## Dateien pro Funktion

| Funktion | Hauptdatei | Tests |
|----------|------------|-------|
| Booking Flow | `routes.py` | `test_webhook_routes.py` |
| MagicLine API | `booking_service.py` | `test_booking_service.py` |
| Data Extraction | `extraction_service.py` | `test_extraction_service.py` |
| Text Parsing | `text_parser.py` | `test_text_parser.py` |
| LLM Chat | `chat_service.py` | `test_chat_service.py` |
| Customer Data | `customer_service.py` | `test_customer_service.py` |
| Constants | `constants.py` | `test_constants.py` |

---

*Letzte Aktualisierung: 2026-01-09*
