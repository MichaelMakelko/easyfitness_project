"""Unit tests for WhatsAppClient with mocked requests."""

import pytest
import responses
from requests.exceptions import RequestException

from api.whatsapp_client import WhatsAppClient, send_whatsapp_message


@pytest.fixture
def whatsapp_client():
    """Create WhatsAppClient instance for testing."""
    return WhatsAppClient()


class TestWhatsAppClientInit:
    """Tests for WhatsAppClient initialization."""

    def test_init_sets_phone_number_id(self, whatsapp_client):
        """Test phone_number_id is set from config."""
        assert whatsapp_client.phone_number_id is not None

    def test_init_sets_access_token(self, whatsapp_client):
        """Test access_token is set from config."""
        assert whatsapp_client.access_token is not None

    def test_init_sets_headers(self, whatsapp_client):
        """Test authorization header is set."""
        assert "Authorization" in whatsapp_client.headers
        assert whatsapp_client.headers["Authorization"].startswith("Bearer ")

    def test_messages_url_property(self, whatsapp_client):
        """Test messages_url property returns correct URL."""
        expected_url = f"https://graph.facebook.com/v22.0/{whatsapp_client.phone_number_id}/messages"
        assert whatsapp_client.messages_url == expected_url


class TestSendMessage:
    """Tests for send_message method."""

    @responses.activate
    def test_send_message_success(self, whatsapp_client):
        """Test successful message sending."""
        responses.add(
            responses.POST,
            whatsapp_client.messages_url,
            json={"messaging_product": "whatsapp", "contacts": [{"wa_id": "491234567890"}]},
            status=200,
        )

        result = whatsapp_client.send_message("491234567890", "Test message")

        assert result is True

    @responses.activate
    def test_send_message_failure(self, whatsapp_client):
        """Test message sending failure."""
        responses.add(
            responses.POST,
            whatsapp_client.messages_url,
            json={"error": {"message": "Invalid token"}},
            status=401,
        )

        result = whatsapp_client.send_message("491234567890", "Test message")

        assert result is False

    @responses.activate
    def test_send_message_payload_structure(self, whatsapp_client):
        """Test correct payload structure is sent."""
        responses.add(
            responses.POST,
            whatsapp_client.messages_url,
            json={},
            status=200,
        )

        whatsapp_client.send_message("491234567890", "Hello!")

        request_body = responses.calls[0].request.body
        # Ensure body is bytes for comparison
        if isinstance(request_body, str):
            request_body = request_body.encode()
        assert request_body is not None
        assert b'"messaging_product": "whatsapp"' in request_body
        assert b'"to": "491234567890"' in request_body
        assert b'"type": "text"' in request_body
        assert b'"body": "Hello!"' in request_body

    @responses.activate
    def test_send_message_500_error(self, whatsapp_client):
        """Test handling of 500 server error."""
        responses.add(
            responses.POST,
            whatsapp_client.messages_url,
            json={"error": "Internal server error"},
            status=500,
        )

        result = whatsapp_client.send_message("491234567890", "Test")

        assert result is False


class TestSendTemplateMessage:
    """Tests for send_template_message method."""

    @responses.activate
    def test_send_template_message_success(self, whatsapp_client):
        """Test successful template message sending."""
        responses.add(
            responses.POST,
            whatsapp_client.messages_url,
            json={},
            status=200,
        )

        result = whatsapp_client.send_template_message("491234567890", "test_template")

        assert result is True

    @responses.activate
    def test_send_template_message_removes_plus(self, whatsapp_client):
        """Test plus sign is removed from phone number."""
        responses.add(
            responses.POST,
            whatsapp_client.messages_url,
            json={},
            status=200,
        )

        whatsapp_client.send_template_message("+491234567890", "test_template")

        request_body = responses.calls[0].request.body
        # Ensure body is bytes for comparison
        if isinstance(request_body, str):
            request_body = request_body.encode()
        assert request_body is not None
        assert b"+49" not in request_body
        assert b'"to": "491234567890"' in request_body

    @responses.activate
    def test_send_template_message_payload_structure(self, whatsapp_client):
        """Test correct template payload structure."""
        responses.add(
            responses.POST,
            whatsapp_client.messages_url,
            json={},
            status=200,
        )

        whatsapp_client.send_template_message("491234567890", "my_template", "de_DE")

        request_body = responses.calls[0].request.body
        # Ensure body is bytes for comparison
        if isinstance(request_body, str):
            request_body = request_body.encode()
        assert request_body is not None
        assert b'"type": "template"' in request_body
        assert b'"name": "my_template"' in request_body

    @responses.activate
    def test_send_template_message_failure(self, whatsapp_client):
        """Test template message failure."""
        responses.add(
            responses.POST,
            whatsapp_client.messages_url,
            json={"error": "Template not found"},
            status=404,
        )

        result = whatsapp_client.send_template_message("491234567890", "invalid_template")

        assert result is False


class TestSendOutboundMessage:
    """Tests for send_outbound_message method."""

    @responses.activate
    def test_send_outbound_message_success(self, whatsapp_client):
        """Test successful outbound message sending."""
        responses.add(
            responses.POST,
            whatsapp_client.messages_url,
            json={},
            status=200,
        )

        result = whatsapp_client.send_outbound_message("+491234567890", "Hello!")

        assert result is True

    @responses.activate
    def test_send_outbound_message_removes_plus(self, whatsapp_client):
        """Test plus sign is removed from phone number."""
        responses.add(
            responses.POST,
            whatsapp_client.messages_url,
            json={},
            status=200,
        )

        whatsapp_client.send_outbound_message("+491234567890", "Hello!")

        request_body = responses.calls[0].request.body
        # Ensure body is bytes for comparison
        if isinstance(request_body, str):
            request_body = request_body.encode()
        assert request_body is not None
        assert b'"to": "491234567890"' in request_body

    @responses.activate
    def test_send_outbound_message_failure(self, whatsapp_client):
        """Test outbound message failure."""
        responses.add(
            responses.POST,
            whatsapp_client.messages_url,
            json={"error": "Rate limited"},
            status=429,
        )

        result = whatsapp_client.send_outbound_message("+491234567890", "Hello!")

        assert result is False


class TestConvenienceFunctions:
    """Tests for module-level convenience functions."""

    @responses.activate
    def test_send_whatsapp_message_function(self):
        """Test send_whatsapp_message convenience function."""
        # Reset singleton client
        import api.whatsapp_client as wc
        wc._client = None

        client = WhatsAppClient()
        responses.add(
            responses.POST,
            client.messages_url,
            json={},
            status=200,
        )

        result = send_whatsapp_message("491234567890", "Test")

        assert result is True
