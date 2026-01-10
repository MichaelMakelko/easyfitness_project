# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

German-language WhatsApp chatbot for EasyFitness EMS Braunschweig fitness studio. Uses a local Llama 3.1 8B LLM (4-bit quantized) to simulate "Max" - a fitness trainer persona who engages with leads and books trial training sessions via the MagicLine booking API.

## Commands

### Setup
```bash
# Create virtual environment
python -m venv .venv
.venv\Scripts\activate  # Windows

# Install PyTorch with CUDA 12.1 FIRST
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121

# Then install other dependencies
pip install -r src/requirements.txt
```

### Running
```bash
cd src
python main.py  # Runs Flask on http://localhost:5000
```
Requires ngrok or similar for WhatsApp webhook tunneling.

### Utility Scripts
```bash
python scripts/send_with_template.py  # Send template messages
python scripts/start_chat_with_anyone.py  # Initiate chats (needs import path fix)
python scripts/diagnose.py  # Diagnostic utility
```
**Note:** Some scripts have outdated import paths. Update imports to use:
- `from api.whatsapp_client import send_outbound_message`
- `from services.customer_service import CustomerService`

## Architecture

```
WhatsApp Message → Flask Webhook (routes.py)
    → CustomerService (load customer from JSON)
    → ChatService (build prompt with history + profile)
    → LlamaBot (generate JSON response)
    → BookingService (if appointment intent detected → MagicLine API)
    → WhatsAppClient (send reply)
    → CustomerService (save updated history + profile)
```

### Key Components

- **LlamaBot** (`src/model/llama_model.py`): Llama 3.1 8B with 4-bit BitsAndBytes quantization. Requires ~7.6GB VRAM.
- **ChatService** (`src/services/chat_service.py`): Builds prompts from `src/prompts/fitnesstrainer_prompt.txt`, parses JSON responses containing `reply` and `profil` fields. Handles 3 response formats (JSON, Python dict, ast.literal_eval).
- **CustomerService** (`src/services/customer_service.py`): Persists customer data and conversation history to `data/customers.json`. Limits history to 100 messages (trims to 80 when full).
- **BookingService** (`src/services/booking_service.py`): MagicLine API integration for appointment validation and booking.
- **ExtractionService** (`src/services/extraction_service.py`): LLM-based data extraction with temperature=0.1 for deterministic JSON output. Validates dates (rejects <2020, >1 year future, >7 days past).
- **WhatsAppClient** (`src/api/whatsapp_client.py`): WhatsApp Cloud API v22.0 wrapper.
- **Constants** (`src/constants.py`): Centralized constants including `CustomerStatus`, `BotMessages`, `ProcessedMessageTracker` (LRU-based duplicate detection), timezone handling, and validation utilities.
- **TextParser** (`src/utils/text_parser.py`): Regex-based extraction for names, emails, dates, times, and booking intent detection.

### Data Storage

All customer data stored in `data/customers.json` (no database). Each customer record includes:
- `name`: Display name (updated from `vorname`)
- `status`: Lead status (neuer Interessent → Name bekannt → Probetraining gebucht)
- `profil`: Profile fields including:
  - `magicline_customer_id`: MagicLine ID (null for new leads, set manually after registration)
  - `vorname`, `nachname`: Required for Trial Offer booking
  - `email`: Required for Trial Offer booking
  - Other fields: age, gender, fitness goals, health restrictions, etc.
- `history`: Conversation history (role + content)
- `letzter_kontakt`: Last contact timestamp

## Environment Variables

Copy `.env.example` to `.env` and configure:

| Variable | Description |
|----------|-------------|
| `VERIFY_TOKEN` | WhatsApp webhook verification token |
| `ACCESS_TOKEN` | WhatsApp Cloud API access token |
| `PHONE_NUMBER_ID` | WhatsApp Business phone number ID |
| `MODEL_PATH` | Path to local Llama model directory |
| `MAGICLINE_BASE_URL` | MagicLine API base URL |
| `MAGICLINE_API_KEY` | MagicLine API key |
| `MAGICLINE_BOOKABLE_ID_TRIAL_OFFER` | Bookable ID for trial offer appointments (Probetraining = 30 min) |
| `MAGICLINE_STUDIO_ID` | Studio ID |
| `MAGICLINE_TEST_CUSTOMER_ID` | Test customer ID for development |
| `MAGICLINE_TRIAL_OFFER_CONFIG_ID` | Config ID for trial offer bookings |
| `EMAIL_SENDER` | (Optional) Email sender address |
| `EMAIL_PASSWORD` | (Optional) Email password |
| `EMAIL_SMTP_SERVER` | (Optional) SMTP server, default: smtp.gmail.com |
| `EMAIL_SMTP_PORT` | (Optional) SMTP port, default: 587 |

## Booking Flow

### Intent Detection (`text_parser.py`)
Booking is triggered when:
- Message contains booking keyword (`probetraining`, `termin`, `buchen`, etc.)
- AND contains date (`25.12.`, `25.12.2025`, weekday names) OR time (`10:00`, `10 Uhr`)

### Date/Time Parsing
- `extract_date_only()`: Extracts date, assumes current year if only DD.MM. given
- `extract_time_only()`: Extracts time from `HH:MM` or `X Uhr` format
- `extract_date_time()`: Only returns value if BOTH date AND time are present
- If only date given → Bot asks for time (no default value)

### MagicLine API - Two Booking Flows

**1. Registered Customer Flow** (has `magicline_customer_id`):
- Uses `/appointments/booking/book` endpoint
- Requires: `customerId`, `bookableAppointmentId`, `startDateTime`, `endDateTime`

**2. Trial Offer Flow** (new leads without `magicline_customer_id`):
- Uses `/trial-offers/` endpoints for lead management, regular `/appointments/` for booking
- Steps:
  1. `POST /trial-offers/lead/validate` - Validate lead data
  2. `POST /trial-offers/lead/create` - Create lead in MagicLine → returns `leadCustomerId`
  3. `POST /appointments/bookable/validate` - Validate slot (with `leadCustomerId` as `customerId`)
  4. `POST /appointments/booking/book` - Book appointment (with `leadCustomerId` as `customerId`)
- Required data: `vorname`, `nachname`, `email`, `slotStart`, `slotEnd`
- Bot asks for missing data before attempting booking

**General:**
- Probetraining duration: **30 minutes**
- Validates slot availability before booking

### Fallback Data Request System

The `_ensure_asks_for_missing_data()` function in `routes.py` ensures the bot asks for missing booking data if the LLM forgets. Priority order:

**For new leads:** vorname → nachname → email → datum → uhrzeit
**For existing customers:** datum → uhrzeit (no personal data needed)

### Booking Keywords

Booking intent is detected when message contains a keyword + date/time:
- `probetraining`, `probentraining`, `termin`, `buchen`, `buchung`, `anmelden`, `reservieren`
- `vorbeikommen`, `vorbei kommen`, `ausprobieren`, `testen`, `probieren`
- `einbuchen`, `eintragen`, `training machen`, `training buchen`

**Note:** `kommen` was removed (too generic, caused false positives like "kann nicht kommen")

## Customer Data Handling

### RAM vs JSON
- On server start: `customers.json` is loaded **once** into RAM
- All reads come from RAM (fast)
- All writes update RAM + save to JSON immediately
- **Important**: Manual edits to `customers.json` require server restart

### Duplicate Message Handling
WhatsApp sends retries if response is slow. The bot tracks processed message IDs to prevent duplicate processing.

## Bot Date Awareness

The system prompt includes current date (`{{WOCHENTAG}}`, `{{DATUM}}`), injected dynamically via `ChatService.build_system_prompt()`. The bot always knows today's date.

## Key Constraints

- **German language only**: All prompts, customer interactions, and parsing assume German
- **Local LLM**: Model runs on local GPU with 4-bit quantization (no cloud LLM API)
- **JSON file persistence**: No database - all data in `data/customers.json`
- **Persona requirement**: LLM must never reveal it's an AI - always acts as "Max"
- **Response format**: LLM outputs JSON with `reply` (message text) and `profil` (extracted customer data)

---

## Session Notes (2026-01-05) - Major Bug Fixes

### Overview
Fixed critical bugs preventing the booking flow from working correctly. The main issues were:
1. LLM extraction unreliable (wrong dates, missing time, invalid JSON)
2. Booking intent not detected when user split data across messages
3. Data persistence bugs
4. Response parsing failures when LLM returned Python dict syntax

### All Files Modified

#### 1. `src/constants.py` (NEW FILE)
**Created centralized constants module with:**
- `CustomerStatus` class - status constants ("neuer Interessent", "Name bekannt", etc.)
- `BotMessages` class - all hardcoded German response strings
- `ProcessedMessageTracker` - thread-safe LRU-based duplicate message detection
- `validate_email()`, `validate_name()` - validation functions
- `get_timezone_offset()` - dynamic CET/CEST timezone
- `build_datetime_iso()` - builds ISO datetime with correct timezone
- `format_date_german()` - formats YYYY-MM-DD to DD.MM.YYYY
- `message_tracker` - global instance for duplicate detection

**Why:** Eliminated hardcoded strings scattered across files, centralized validation, fixed timezone being hardcoded to +01:00.

#### 2. `src/api/routes.py`
**Changes:**
- Import `build_datetime_iso`, `format_date_german`, `message_tracker` from constants
- Import `extract_date_only`, `extract_time_only` from text_parser
- **Hybrid extraction**: LLM extraction + regex fallback for date/time
- **Context persistence**: Store extracted `datum` in profile for multi-message booking
- **Context-aware booking intent**: Pass customer context to `extract_booking_intent()`
- **Data persistence fix**: `customer["last_booking_id"]` now saved via `update_profil()`
- **KeyError safety**: Use `.get()` for message fields instead of direct access

**Why:** LLM extraction was unreliable (missed "15 Uhr", gave wrong dates). Regex fallback ensures date/time extraction works. Context allows multi-message booking flow.

#### 3. `src/services/chat_service.py`
**Changes:**
- `_parse_response()` now handles 3 formats:
  1. Standard JSON (double quotes)
  2. Python dict syntax (single quotes) - converted to JSON
  3. `ast.literal_eval()` fallback for Python literals
- Added `_extract_reply_profil()` helper method

**Why:** LLM sometimes returned `{'reply': '...'}` (Python syntax with single quotes) instead of `{"reply": "..."}` (valid JSON). This caused the entire dict to be sent to WhatsApp as the message.

#### 4. `src/services/extraction_service.py`
**Changes:**
- Improved prompt with explicit examples:
  - `morgen = {tomorrow}` (actual date)
  - `übermorgen = {day_after_tomorrow}` (actual date)
  - `"15 Uhr" → "15:00"` examples
- Added weekday to prompt: "Heute ist {weekday}, der {today}"
- Enhanced date validation:
  - Reject dates before 2020 (placeholders like 1970-01-01)
  - Reject dates > 1 year in future
  - Reject dates > 7 days in past
- Removed duplicate `build_datetime_iso()` method (uses constants version)

**Why:** LLM gave wrong dates for "morgen" (6 months off), placeholder dates like 1970-01-01, 0000-00-00 were accepted.

#### 5. `src/services/customer_service.py`
**Changes:**
- Added `datum` and `uhrzeit` fields to default profile (for multi-message booking)
- Added `last_booking_id` field to default profile
- Uses `BotMessages`, `CustomerStatus` from constants

**Why:** Needed to store partial booking data between messages. Booking ID was set but never persisted.

#### 6. `src/utils/text_parser.py`
**Changes:**
- `extract_booking_intent()` now accepts optional `customer_context` parameter
- Expanded booking keywords:
  - Added: "probentraining" (LLM variant), "kommen", "vorbei", "testen", "probieren", "gebucht", "reservierung", "einbuchen", "eintragen"
- Context-aware detection:
  - If customer has name+email AND provides date/time → booking intent = True
  - If customer has stored datum AND provides time → booking intent = True

**Why:** Booking intent was False when user said "Probetraining" in message 2 but gave date in message 4. Keywords didn't include LLM variations ("Probentraining" vs "probetraining").

#### 7. `src/api/__init__.py`
**Changes:**
- Removed `from api.routes import webhook_bp` to prevent LlamaBot loading during test imports

**Why:** Tests failed with HFValidationError because LlamaBot was instantiated at import time.

#### 8. `src/main.py`
**Changes:**
- Direct import: `from api.routes import webhook_bp`

**Why:** Part of import chain fix.

#### 9. Test Files Updated
- `tests/unit/test_extraction_service.py` - Use dynamic `future_date` fixture
- `tests/unit/test_chat_service.py` - Added 3 tests for Python dict parsing
- `tests/integration/test_booking_flow.py` - Use dynamic `future_date` fixture
- `tests/integration/test_webhook_routes.py` - Use `message_tracker.clear()` instead of patching

### Current Test Status
**196 tests passing** (was 193 before session, added 3 new tests)

### Booking Flow - How It Works Now

```
1. User: "Ich heiße Michael Makelko und würde gerne ein Probetraining machen"
   → Extraction: vorname="Michael", nachname="Makelko"
   → Saved to profile
   → Bot asks for email

2. User: "meine email ist michael@test.de"
   → Extraction: email="michael@test.de"
   → Saved to profile
   → Bot asks for date/time

3. User: "Wie wäre es am 10.01.2026?"
   → LLM extraction fails (returns [])
   → Regex fallback: extract_date_only() → "2026-01-10"
   → Saved to profile (datum)
   → Booking intent: True (has_booking_data=True + has_date)
   → No time → Bot asks: "Um welche Uhrzeit möchtest du am 10.01.2026 vorbeikommen?"

4. User: "Um 15 Uhr"
   → LLM extraction fails
   → Regex fallback: extract_time_only() → "15:00"
   → Context: profil.datum = "2026-01-10"
   → Booking intent: True (has_partial_datetime=True + has_time)
   → build_datetime_iso("2026-01-10", "15:00") → "2026-01-10T15:00:00+01:00"
   → API call to MagicLine!
```

### Known Limitations / Future Work
~~1. **LLM extraction still unreliable** - Fixed: Added `generate_extraction()` with temperature=0.1~~
~~2. **Attention mask warning** - Fixed: Proper pad_token configuration~~
~~3. **No booking confirmation persistence** - Fixed: Added `bookings` list with full booking history~~

All major limitations from 2026-01-05 session have been addressed in the 2026-01-06 session.

---

## Session Notes (2026-01-06) - Live Test Fixes

### Overview
Fixed critical bugs discovered during live testing where booking conversations were failing to complete.

### Key Issues Fixed

#### 1. Date Parsing for "am 9.1" Format
- Extended `extract_date_only()` to handle German short date format without trailing dot
- Added `_build_date_with_smart_year()` for intelligent year selection at year boundaries
- Now correctly parses: "am 9.1", "den 15.3", "9.1 um 10 Uhr"

#### 2. Name Extraction from "Name, email" Format
- Added `extract_full_name()` function to extract both vorname and nachname
- Supports: "Britney Spears, email@test.de", "Ich heiße Max Mustermann", "Max Mustermann"
- Added regex fallback for name extraction in `_handle_text_message()`

#### 3. Extraction Priority Swap (Critical Fix)
- **Before:** LLM first, regex fallback → LLM often returned wrong dates, overriding correct regex matches
- **After:** Regex FIRST, LLM fallback → Regex is reliable for explicit dates, LLM only for complex cases like "morgen"

#### 4. Auto-Trigger Booking When All Data Complete
- If profile has all required data (vorname, nachname, email, datum, uhrzeit), booking is auto-triggered
- Handles case where user provides last missing piece without saying "buchen" again

#### 5. Profile Data Persistence Strategy
- `_handle_booking_if_needed()` now follows 5-step strategy:
  1. Load ALL stored profile data
  2. Extract from current message (regex first, LLM fallback)
  3. Merge: new data takes priority over stored
  4. Check what's missing → ask or proceed
  5. Book with complete data

### Files Modified

- **`src/utils/text_parser.py`**: Added `extract_full_name()`, `_is_valid_name()`, extended date regex
- **`src/api/routes.py`**: Swapped extraction priority, added auto-trigger, added name/email regex fallback
- **`tests/unit/test_text_parser.py`**: Added 21 new tests for `extract_full_name()` and date parsing

### Current Test Status
**219 tests passing** (was 198 before, added 21 new tests)

### Key Code Patterns

**Regex-First Extraction (routes.py:241-266):**
```python
# === STEP 2: Extract from current message ===
# IMPORTANT: Regex FIRST (more reliable), then LLM for complex cases like "morgen"
new_date = extract_date_only(text)
new_time = extract_time_only(text)

# LLM fallback for complex cases (e.g., "morgen", "nächsten Montag")
if not new_date:
    llm_date = extracted_data.get("datum")
    if llm_date:
        new_date = llm_date
```

**Auto-Trigger Complete Booking (routes.py:229-235):**
```python
all_data_complete = bool(
    stored_vorname and stored_nachname and stored_email and
    stored_date and stored_time
)
if all_data_complete and not booking_intent:
    print(f"📅 Alle Daten komplett - Auto-Trigger Buchung!")
    booking_intent = True
```

**Context-Aware Booking Intent (text_parser.py):**
```python
if customer_context:
    if has_booking_data and (has_date or has_time):
        return True  # Customer in booking flow
    if has_partial_datetime and (has_date or has_time):
        return True  # Has stored datum, now providing time
```

**Multi-Format Response Parsing (chat_service.py):**
```python
# Try 1: Standard JSON
data = json.loads(json_str)
# Try 2: Python dict syntax (single quotes)
fixed_str = json_str.replace("'", '"').replace("None", "null")
data = json.loads(fixed_str)
# Try 3: ast.literal_eval
data = ast.literal_eval(json_str)
```

---

## Session Notes (2026-01-06 #2) - Booking Status Context for LLM

### Overview
Added booking status context to the LLM system prompt so the bot knows what data is present/missing for booking and can respond more intelligently.

### Problem Solved
Previously, the bot often:
- Asked for data it already had (e.g., asking for name when `vorname` was stored)
- Said "Ich buche dich ein!" when required data was missing
- Gave contradictory responses (LLM said one thing, system overrode with hardcoded message)

### Solution: Booking Status in System Prompt
The LLM now receives a structured `[BUCHUNGSSTATUS]` section with only booking-relevant fields:

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

With clear instructions:
- If a field is `null` → ask for it (ONE question per message)
- If a field has a value → DON'T ask again
- `ist_bestandskunde: true` → only needs datum + uhrzeit (not name/email)
- All fields filled → confirm booking

### Files Modified

#### 1. `src/services/chat_service.py`
- Added `_build_booking_status(profil)` method
- Modified `build_system_prompt()` to inject `{{BUCHUNGSSTATUS}}`

```python
def _build_booking_status(self, profil: dict[str, Any]) -> dict[str, Any]:
    is_existing_customer = bool(profil.get("magicline_customer_id"))
    return {
        "ist_bestandskunde": is_existing_customer,
        "vorname": profil.get("vorname"),
        "nachname": profil.get("nachname"),
        "email": profil.get("email"),
        "datum": profil.get("datum"),
        "uhrzeit": profil.get("uhrzeit"),
    }
```

#### 2. `src/prompts/fitnesstrainer_prompt.txt`
- Added `[BUCHUNGSSTATUS]` section with clear rules and examples

#### 3. `tests/conftest.py`
- Updated `temp_prompt_file` fixture to include `{{BUCHUNGSSTATUS}}`

#### 4. `tests/unit/test_chat_service.py`
- Added 6 new tests for `_build_booking_status()`:
  - `test_build_booking_status_new_customer`
  - `test_build_booking_status_existing_customer`
  - `test_build_booking_status_partial_data`
  - `test_build_booking_status_complete_data`
  - `test_build_booking_status_empty_profil`
  - `test_build_booking_status_only_includes_booking_fields`

### Current Test Status
**227 tests passing** (was 221 before, added 6 new tests)

### Architecture Decision: Keep Extraction Separate
We chose **Option A**: Profil-Context + Extraction behalten

- **Regex/LLM extraction remains separate** → reliable data extraction
- **Bot gets profile context** → intelligent responses
- **Hardcoded messages stay as fallback** → safety net if LLM misbehaves

This is a non-breaking, additive change that improves bot intelligence without risking the extraction pipeline.

---

## Session Notes (2026-01-08) - Date Bug Fix & 1-Sentence Responses

### Overview
Fixed critical bug where wrong dates were stored after booking failures, and enforced max 1 sentence per bot response.

### Issues Found in Live Test (Customer 491635130645)

| Issue | Severity | Description |
|-------|----------|-------------|
| Wrong date persisted | CRITICAL | After booking failure (09.01), bot kept asking about 08.01 |
| Responses too long | HIGH | Bot gave 2-4 sentences instead of 1 |
| LLM went off-topic | HIGH | When asked for name/email, LLM asked about "Alter" instead |

### Root Cause Analysis

**Bug 1: Date Overwrite from Chat LLM**
- Chat LLM's `profil` response included `datum` extracted from conversation HISTORY
- After booking failure cleared `datum=None`, next message's Chat LLM response re-injected old date
- Location: `routes.py:185-191` - `extracted_profil` update didn't exclude dates

**Bug 2: Response Length**
- Prompt said "Maximal 2-3 kurze Sätze" but user wanted MAX 1 sentence

### Files Modified

#### 1. `src/api/routes.py`
- Added `excluded_fields = {"datum", "uhrzeit"}` to Chat LLM profil update
- Prevents Chat LLM from overwriting dates extracted from conversation history

```python
# CRITICAL: Exclude datum/uhrzeit - Chat LLM extracts these from conversation
# history which causes wrong dates after booking failure clears them
excluded_fields = {"datum", "uhrzeit"}
llm_only_fields = {
    k: v for k, v in extracted_profil.items()
    if v is not None and not extracted_data.get(k) and k not in excluded_fields
}
```

#### 2. `src/prompts/fitnesstrainer_prompt.txt`
- Changed "Maximal 2-3 kurze Sätze" → "MAXIMAL EIN SATZ pro Nachricht (STRIKT!)"
- Added Rule 4: "Wenn Daten fehlen und Kunde antwortet mit etwas anderem → TROTZDEM nach den fehlenden Daten fragen!"
- Shortened all examples to single sentences

#### 3. `src/services/booking_service.py`
- Fixed comment: "default 20 for EMS" → "default 30 min for Probetraining"

#### 4. `tests/integration/test_webhook_routes.py`
- Added `TestLLMProfilDateExclusion` test class
- Test verifies datum/uhrzeit are excluded from Chat LLM profil updates

### Current Test Status
**321 tests passing** (was 320 before, added 1 new test)

### Key Design Decisions

**Why exclude datum/uhrzeit from Chat LLM profil?**
- Chat LLM sees full conversation history in system prompt
- It extracts dates mentioned in history (e.g., "08.01.2026" from bot's earlier message)
- This causes wrong dates after `clear_booking_request()` clears the correct date
- ExtractionService and regex handle dates independently per-message

**Date Extraction Priority (unchanged):**
1. Regex extraction (most reliable for explicit dates)
2. ExtractionService LLM (for complex cases like "morgen")
3. ~~Chat LLM profil~~ (NOW EXCLUDED for dates)

### Booking Keywords (Updated List)
```python
booking_keywords = [
    "probetraining", "probentraining", "probe training",
    "termin", "buchen", "buchung", "gebucht",
    "anmelden", "anmeldung", "reservieren", "reservierung",
    "training machen", "training buchen",
    "vorbeikommen", "vorbei kommen",  # "kommen" alone removed (too generic)
    "ausprobieren", "testen", "probieren",
    "einbuchen", "eintragen",
]
```

---

## Session Notes (2026-01-09) - Slot Availability Pre-Check

### Overview
Added slot availability pre-check to prevent creating leads when requested time slots are already booked. Previously, leads were created in MagicLine even when the slot was unavailable, causing unnecessary data in the system.

### Problem Solved
**Before:**
1. User requests: "Probetraining am 15.01. um 14:00"
2. System validates lead → creates lead in MagicLine
3. System validates slot → "Slot not available"
4. **Result:** Lead created but booking failed = Lead garbage in MagicLine

**After:**
1. User requests: "Probetraining am 15.01. um 14:00"
2. System checks slot availability FIRST via GET endpoint
3. If unavailable → Returns alternative times, **NO lead created**
4. If available → Proceeds with lead creation and booking

### New Trial Offer Booking Flow

```
VORHER (4 API-Calls):              NACHHER (5 API-Calls):
                                   0. GET /trial-offers/.../slots ← PRE-CHECK
1. POST validate_lead              1. POST validate_lead
2. POST create_lead                2. POST create_lead
3. POST validate_appointment       3. POST validate_appointment
4. POST book_appointment           4. POST book_appointment
```

**Key behavior:**
- If pre-check fails with API error → Fallback to old flow (backwards compatible)
- If slot not available → Early return with alternatives, NO lead created
- If slot available → Continue with full booking flow

### Files Modified

#### 1. `src/services/booking_service.py`
**Added 8 new methods for slot availability:**

| Method | Purpose |
|--------|---------|
| `get_available_slots(date)` | GET `/trial-offers/appointments/{id}/slots` |
| `check_slot_availability(start_datetime)` | Public pre-check API |
| `_extract_date_from_datetime(iso)` | Extract YYYY-MM-DD from ISO datetime |
| `_extract_time_from_datetime(iso)` | Extract HH:MM from ISO datetime |
| `_is_slot_in_list(target, slots)` | Check if slot exists in list |
| `_get_alternative_slots(target, slots)` | Find closest alternatives |
| `_time_to_minutes(time_str)` | Convert HH:MM to minutes |

**Modified `try_book_trial_offer()`:**
```python
# Step 0: PRE-CHECK slot availability BEFORE creating lead
slot_check = self.check_slot_availability(start_datetime, duration_minutes)

if not slot_check.get("api_error"):
    if not slot_check.get("available"):
        alternatives = slot_check.get("alternatives", [])
        if alternatives:
            return False, BotMessages.slot_unavailable_with_alternatives(alternatives), None
        else:
            return False, BotMessages.BOOKING_SLOT_UNAVAILABLE, None
    print(f"   ✅ Slot verfügbar (Pre-Check)")
else:
    # API error - continue with old flow as fallback
    print(f"   ⚠️ Pre-Check fehlgeschlagen - fahre mit altem Flow fort")
```

#### 2. `src/constants.py`
**Added new BotMessage method:**
```python
@staticmethod
def slot_unavailable_with_alternatives(alternatives: list[str]) -> str:
    """
    Message when requested slot is not available but alternatives exist.
    Returns German message like:
    "Diese Zeit ist leider belegt. Verfügbar wäre: 13:00 Uhr, 15:00 Uhr oder 16:00 Uhr."
    """
```

#### 3. `tests/fixtures/magicline_responses.py`
**Added slot response fixtures:**
- `SLOTS_AVAILABLE` - List of 6 available slots
- `SLOTS_EMPTY` - Empty slot list
- `create_slots_response()` - Configurable slot response helper

#### 4. Test Files Updated
- `tests/unit/test_booking_service.py` - +33 new tests for slot availability
- `tests/unit/test_session_changes.py` - +5 new tests for `slot_unavailable_with_alternatives()`
- `tests/integration/test_booking_flow.py` - Updated existing tests for new flow

### Current Test Status
**354 tests passing** (was 321 before, added 33 new tests)

### New API Endpoint Used

```
GET /v1/trial-offers/appointments/{bookableAppointmentId}/slots
Query params: date=YYYY-MM-DD, duration=30

Response formats supported:
1. List: [{"startDateTime": "...", "endDateTime": "..."}]
2. Dict: {"slots": [...]}
```

### Key Code Patterns

**Pre-Check with Fallback (booking_service.py:684-701):**
```python
slot_check = self.check_slot_availability(start_datetime, duration_minutes)

if not slot_check.get("api_error"):
    # API succeeded - trust the result
    if not slot_check.get("available"):
        alternatives = slot_check.get("alternatives", [])
        if alternatives:
            return False, BotMessages.slot_unavailable_with_alternatives(alternatives), None
        return False, BotMessages.BOOKING_SLOT_UNAVAILABLE, None
else:
    # API error - fallback to old flow
    pass  # Continue with lead creation
```

**Alternative Slots Sorted by Distance (booking_service.py:357-411):**
```python
def _get_alternative_slots(self, target_datetime, slots, max_alternatives=3):
    target_minutes = self._time_to_minutes(target_time)

    slot_distances = []
    for slot in slots:
        slot_minutes = self._time_to_minutes(slot_time)
        distance = abs(slot_minutes - target_minutes)
        slot_distances.append((slot_time, distance))

    slot_distances.sort(key=lambda x: x[1])
    return [time for time, _ in slot_distances[:max_alternatives]]
```

**German Message Formatting (constants.py:60-84):**
```python
@staticmethod
def slot_unavailable_with_alternatives(alternatives: list[str]) -> str:
    formatted = [f"{time} Uhr" for time in alternatives]

    if len(formatted) == 1:
        return f"Diese Zeit ist leider belegt. Wie wäre es um {formatted[0]}?"
    elif len(formatted) == 2:
        return f"Diese Zeit ist leider belegt. Verfügbar wäre: {formatted[0]} oder {formatted[1]}."
    else:
        last = formatted[-1]
        rest = ", ".join(formatted[:-1])
        return f"Diese Zeit ist leider belegt. Verfügbar wäre: {rest} oder {last}."
```

### Example User Flow

```
User: "Probetraining am 15.01. um 14:00"

CASE A - Slot available:
   → GET slots: [13:00, 14:00, 15:00, 16:00]
   → 14:00 in list ✓
   → Continue with booking
   → "Termin gebucht! Bestätigung per E-Mail unterwegs."

CASE B - Slot not available:
   → GET slots: [10:00, 11:00, 16:00, 17:00]
   → 14:00 NOT in list
   → Find alternatives closest to 14:00: [16:00, 11:00, 17:00]
   → "Diese Zeit ist leider belegt. Verfügbar wäre: 16:00 Uhr, 11:00 Uhr oder 17:00 Uhr."
   → NO lead created!

CASE C - API error:
   → GET slots: 500 Server Error
   → api_error=True → Fallback to old flow
   → Create lead, validate slot, get error there
   → (Backwards compatible)
```

### Architecture Decision

**Why pre-check instead of modifying validation step?**
1. **Clean separation**: Slot check is independent of lead management
2. **Better UX**: User gets alternatives immediately
3. **Backwards compatible**: API errors fall back to old flow
4. **No lead garbage**: Prevents unnecessary lead creation

### MagicLine OpenAPI Reference

The implementation uses the MagicLine OpenAPI endpoint documented at:
- [Trial Offers API](https://developer.sportalliance.com/apis/magicline/openapi/openapi/trial-offers)
- Base URL: `https://<tenant>.open-api.magicline.com/v1`
- Auth: `X-API-KEY` header
