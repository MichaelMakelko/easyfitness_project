"""Integration tests for Flask webhook routes."""

import json
import pytest
from unittest.mock import MagicMock, patch
from flask import Flask

from tests.fixtures.whatsapp_payloads import (
    create_webhook_payload,
    create_status_update_payload,
)


@pytest.fixture
def app():
    """Create Flask test app with mocked dependencies."""
    # Mock LlamaBot before importing routes
    with patch("model.llama_model.LlamaBot") as mock_llm_class:
        mock_llm_instance = MagicMock()
        mock_llm_instance.generate.return_value = '{"reply": "Test reply", "profil": {}}'
        mock_llm_class.return_value = mock_llm_instance

        # Import app after mocking
        from main import app
        app.config["TESTING"] = True
        yield app


@pytest.fixture
def client(app):
    """Create Flask test client."""
    return app.test_client()


class TestWebhookVerification:
    """Tests for webhook GET verification endpoint."""

    def test_verify_webhook_success(self, client):
        """Test successful webhook verification."""
        response = client.get(
            "/webhook",
            query_string={
                "hub.verify_token": "test_verify_token",
                "hub.challenge": "test_challenge_123",
            },
        )

        assert response.status_code == 200
        assert response.data == b"test_challenge_123"

    def test_verify_webhook_wrong_token(self, client):
        """Test webhook verification fails with wrong token."""
        response = client.get(
            "/webhook",
            query_string={
                "hub.verify_token": "wrong_token",
                "hub.challenge": "test_challenge",
            },
        )

        assert response.status_code == 403

    def test_verify_webhook_missing_params(self, client):
        """Test webhook verification with missing parameters."""
        response = client.get("/webhook")

        # Should return 403 when params missing
        assert response.status_code == 403


class TestWebhookPost:
    """Tests for webhook POST message handling."""

    def test_webhook_empty_payload(self, client):
        """Test webhook handles empty payload gracefully."""
        response = client.post(
            "/webhook",
            data=json.dumps({}),
            content_type="application/json",
        )

        assert response.status_code == 200

    def test_webhook_status_update_ignored(self, client):
        """Test status updates are processed without error."""
        payload = create_status_update_payload()

        response = client.post(
            "/webhook",
            data=json.dumps(payload),
            content_type="application/json",
        )

        assert response.status_code == 200

    def test_webhook_returns_success_json(self, client):
        """Test webhook returns success JSON."""
        response = client.post(
            "/webhook",
            data=json.dumps({}),
            content_type="application/json",
        )

        data = json.loads(response.data)
        assert data.get("success") is True

    def test_webhook_invalid_json(self, client):
        """Test webhook handles invalid JSON gracefully."""
        response = client.post(
            "/webhook",
            data="not valid json",
            content_type="application/json",
        )

        # Should not crash - returns error or handles gracefully
        assert response.status_code in [200, 400]


class TestWebhookMessageProcessing:
    """Tests for webhook message processing logic."""

    @patch("api.routes.send_whatsapp_message")
    @patch("api.routes.customer_service")
    @patch("api.routes.chat_service")
    @patch("api.routes.extraction_service")
    def test_webhook_processes_text_message(
        self, mock_extraction, mock_chat, mock_customer, mock_send, client
    ):
        """Test webhook processes incoming text message."""
        # Clear message tracker before test
        from constants import message_tracker
        message_tracker.clear()

        # Set up mocks
        mock_customer.get.return_value = {
            "name": "du",
            "status": "neuer Interessent",
            "profil": {"magicline_customer_id": None},
            "history": [],
        }
        mock_customer.get_history.return_value = []
        mock_extraction.extract_customer_data.return_value = {
            "vorname": None, "nachname": None, "email": None, "datum": None, "uhrzeit": None
        }
        mock_chat.generate_response.return_value = ("Hallo!", {})
        mock_send.return_value = True

        payload = create_webhook_payload(text="Hallo!")

        response = client.post(
            "/webhook",
            data=json.dumps(payload),
            content_type="application/json",
        )

        assert response.status_code == 200

    @patch("api.routes.send_whatsapp_message")
    @patch("api.routes.customer_service")
    @patch("api.routes.chat_service")
    @patch("api.routes.extraction_service")
    def test_webhook_extracts_customer_name(
        self, mock_extraction, mock_chat, mock_customer, mock_send, client
    ):
        """Test webhook extracts and saves customer name."""
        # Clear message tracker before test
        from constants import message_tracker
        message_tracker.clear()

        mock_customer.get.return_value = {
            "name": "du",
            "status": "neuer Interessent",
            "profil": {"magicline_customer_id": None, "vorname": None},
            "history": [],
        }
        mock_customer.get_history.return_value = []
        mock_extraction.extract_customer_data.return_value = {
            "vorname": "Max", "nachname": "Mustermann", "email": None, "datum": None, "uhrzeit": None
        }
        mock_chat.generate_response.return_value = ("Hallo Max!", {"vorname": "Max"})
        mock_send.return_value = True

        payload = create_webhook_payload(text="Ich bin Max Mustermann")

        response = client.post(
            "/webhook",
            data=json.dumps(payload),
            content_type="application/json",
        )

        assert response.status_code == 200
        # Verify update_profil was called
        mock_customer.update_profil.assert_called()


class TestDuplicateMessageHandling:
    """Tests for duplicate message prevention."""

    @patch("api.routes.send_whatsapp_message")
    @patch("api.routes.customer_service")
    @patch("api.routes.chat_service")
    @patch("api.routes.extraction_service")
    def test_first_message_processed(
        self, mock_extraction, mock_chat, mock_customer, mock_send, client
    ):
        """Test first message is processed normally."""
        # Clear message tracker before test
        from constants import message_tracker
        message_tracker.clear()

        mock_customer.get.return_value = {
            "name": "du", "status": "neuer Interessent",
            "profil": {"magicline_customer_id": None}, "history": [],
        }
        mock_customer.get_history.return_value = []
        mock_extraction.extract_customer_data.return_value = {
            "vorname": None, "nachname": None, "email": None, "datum": None, "uhrzeit": None
        }
        mock_chat.generate_response.return_value = ("Reply", {})
        mock_send.return_value = True

        payload = create_webhook_payload(message_id="unique_id_123")

        response = client.post(
            "/webhook",
            data=json.dumps(payload),
            content_type="application/json",
        )

        assert response.status_code == 200


class TestHealthCheck:
    """Tests for health check endpoint if exists."""

    def test_root_endpoint(self, client):
        """Test root endpoint returns something."""
        response = client.get("/")

        # May return 200 or 404 depending on implementation
        assert response.status_code in [200, 404]


class TestWebhookPayloadVariants:
    """Tests for various webhook payload formats."""

    def test_webhook_with_multiple_entries(self, client):
        """Test webhook handles payload with multiple entries."""
        payload = {
            "object": "whatsapp_business_account",
            "entry": [
                {
                    "id": "123",
                    "changes": [{"value": {"messaging_product": "whatsapp"}, "field": "messages"}]
                },
                {
                    "id": "456",
                    "changes": [{"value": {"messaging_product": "whatsapp"}, "field": "messages"}]
                },
            ],
        }

        response = client.post(
            "/webhook",
            data=json.dumps(payload),
            content_type="application/json",
        )

        assert response.status_code == 200

    def test_webhook_with_no_messages(self, client):
        """Test webhook handles payload with no messages field."""
        payload = {
            "object": "whatsapp_business_account",
            "entry": [
                {
                    "id": "123",
                    "changes": [
                        {
                            "value": {
                                "messaging_product": "whatsapp",
                                "metadata": {"phone_number_id": "123"},
                            },
                            "field": "messages",
                        }
                    ],
                }
            ],
        }

        response = client.post(
            "/webhook",
            data=json.dumps(payload),
            content_type="application/json",
        )

        assert response.status_code == 200
