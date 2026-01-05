# api/__init__.py
"""WhatsApp API integration module."""

# NOTE: Do NOT import routes here - it instantiates LlamaBot at module level,
# which breaks test imports. Import webhook_bp directly from api.routes where needed.

from api.whatsapp_client import (
    WhatsAppClient,
    send_outbound_message,
    send_template_message,
    send_whatsapp_message,
)

__all__ = [
    "WhatsAppClient",
    "send_whatsapp_message",
    "send_template_message",
    "send_outbound_message",
]
