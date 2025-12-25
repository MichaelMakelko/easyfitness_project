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
