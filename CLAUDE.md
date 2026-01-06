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
python scripts/start_chat_with_anyone.py  # Initiate chats
python scripts/diagnose.py  # Diagnostic utility
```

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
- **ChatService** (`src/services/chat_service.py`): Builds prompts from `src/prompts/fitnesstrainer_prompt.txt`, parses JSON responses containing `reply` and `profil` fields.
- **CustomerService** (`src/services/customer_service.py`): Persists customer data and conversation history to `data/customers.json`. Limits history to 100 messages.
- **BookingService** (`src/services/booking_service.py`): MagicLine API integration for appointment validation and booking.
- **WhatsAppClient** (`src/api/whatsapp_client.py`): WhatsApp Cloud API v22.0 wrapper.

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
| `MAGICLINE_BOOKABLE_ID` | Bookable ID for appointments (Probetraining = 30 min) |
| `MAGICLINE_STUDIO_ID` | Studio ID |

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
- Uses `/trial-offers/` endpoints
- Steps:
  1. `POST /trial-offers/lead/validate` - Validate lead data
  2. `POST /trial-offers/lead/create` - Create lead in MagicLine
  3. `POST /trial-offers/appointments/booking/validate` - Validate slot
  4. `POST /trial-offers/appointments/booking/book` - Book appointment
- Required data: `vorname`, `nachname`, `email`, `slotStart`, `slotEnd`
- Bot asks for missing data before attempting booking

**General:**
- Probetraining duration: **30 minutes**
- Validates slot availability before booking

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

### Key Code Patterns

**Hybrid Extraction (routes.py):**
```python
# Try LLM first
extracted_date = extracted_data.get("datum")
# Regex fallback if LLM failed
if not extracted_date:
    extracted_date = extract_date_only(text)
    if extracted_date:
        customer_service.update_profil(phone, {"datum": extracted_date})
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
