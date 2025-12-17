# api/whatsapp_client.py
"""WhatsApp Cloud API client for sending messages."""

from typing import Optional

import requests

from config import ACCESS_TOKEN, PHONE_NUMBER_ID


class WhatsAppClient:
    """Client for WhatsApp Cloud API messaging."""

    API_VERSION = "v22.0"
    BASE_URL = f"https://graph.facebook.com/{API_VERSION}"

    def __init__(self):
        self.phone_number_id = PHONE_NUMBER_ID
        self.access_token = ACCESS_TOKEN
        self.headers = {"Authorization": f"Bearer {self.access_token}"}

    @property
    def messages_url(self) -> str:
        """Get messages endpoint URL."""
        return f"{self.BASE_URL}/{self.phone_number_id}/messages"

    def send_message(self, to: str, text: str) -> bool:
        """
        Send a text message (within 24h window or as reply).

        Args:
            to: Recipient phone number
            text: Message text

        Returns:
            True if sent successfully
        """
        payload = {
            "messaging_product": "whatsapp",
            "to": to,
            "type": "text",
            "text": {"body": text},
        }

        response = requests.post(
            self.messages_url, json=payload, headers=self.headers, timeout=10
        )

        if response.status_code != 200:
            print(f"Fehler beim Senden: {response.text}")
            return False
        return True

    def send_template_message(
        self,
        to: str,
        template_name: str = "jaspers_market_plain_text_v1",
        language_code: str = "en_US",
    ) -> bool:
        """
        Send a template message (works anytime, even as first contact).

        Args:
            to: Recipient phone number
            template_name: Approved template name
            language_code: Template language code

        Returns:
            True if sent successfully
        """
        payload = {
            "messaging_product": "whatsapp",
            "to": to.replace("+", ""),
            "type": "template",
            "template": {
                "name": template_name,
                "language": {"code": language_code},
            },
        }

        response = requests.post(
            self.messages_url, json=payload, headers=self.headers, timeout=10
        )

        if response.status_code == 200:
            print(f"Template-Nachricht gesendet an {to}")
            return True
        else:
            print(f"Fehler: {response.status_code} {response.text}")
            return False

    def send_outbound_message(self, to: str, text: str) -> bool:
        """
        Send initial outbound message to new customer.

        Args:
            to: Recipient phone number
            text: Message text

        Returns:
            True if sent successfully
        """
        payload = {
            "messaging_product": "whatsapp",
            "to": to.replace("+", ""),
            "type": "text",
            "text": {"body": text},
        }

        response = requests.post(
            self.messages_url, json=payload, headers=self.headers, timeout=10
        )

        if response.status_code == 200:
            print(f"Erste Nachricht gesendet an {to}")
            return True
        else:
            print(f"Fehler: {response.status_code} → {response.text}")
            return False


# Convenience functions for backwards compatibility
_client: Optional[WhatsAppClient] = None


def _get_client() -> WhatsAppClient:
    """Get or create singleton client instance."""
    global _client
    if _client is None:
        _client = WhatsAppClient()
    return _client


def send_whatsapp_message(to: str, text: str) -> bool:
    """Send WhatsApp message (convenience function)."""
    return _get_client().send_message(to, text)


def send_template_message(to: str, name: str = "du") -> bool:
    """Send template message (convenience function)."""
    return _get_client().send_template_message(to)


def send_outbound_message(to: str, text: str) -> bool:
    """Send outbound message (convenience function)."""
    return _get_client().send_outbound_message(to, text)
