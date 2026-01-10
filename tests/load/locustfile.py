"""Load testing for WhatsApp webhook using Locust.

Run with:
    locust -f tests/load/locustfile.py --host=http://localhost:5000

Then open http://localhost:8089 to configure and start load test.
"""

import json
import random
from locust import HttpUser, task, between

# Import payload helpers
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from fixtures.whatsapp_payloads import create_webhook_payload, BOOKING_MESSAGES, NAME_MESSAGES


class WebhookUser(HttpUser):
    """Simulates WhatsApp webhook traffic."""

    wait_time = between(1, 3)  # Wait 1-3 seconds between tasks

    def on_start(self):
        """Generate unique phone number for this user."""
        self.phone = f"49{random.randint(1000000000, 9999999999)}"
        self.message_counter = 0

    @task(5)
    def send_greeting(self):
        """Simulate greeting message (most common)."""
        greetings = ["Hallo!", "Hi", "Hey", "Guten Tag", "Servus", "Moin"]
        payload = create_webhook_payload(
            phone=self.phone,
            text=random.choice(greetings),
            message_id=f"wamid.greeting_{self.phone}_{self.message_counter}",
        )
        self.message_counter += 1

        self.client.post(
            "/webhook",
            json=payload,
            headers={"Content-Type": "application/json"},
        )

    @task(3)
    def send_question(self):
        """Simulate question about fitness/pricing."""
        questions = [
            "Was kostet das Training bei euch?",
            "Wie funktioniert EMS Training?",
            "Habt ihr Beratungstermine?",
            "Wo seid ihr?",
            "Wann habt ihr geoeffnet?",
            "Wie lange dauert eine Einheit?",
            "Brauche ich Vorkenntnisse?",
        ]
        payload = create_webhook_payload(
            phone=self.phone,
            text=random.choice(questions),
            message_id=f"wamid.question_{self.phone}_{self.message_counter}",
        )
        self.message_counter += 1

        self.client.post(
            "/webhook",
            json=payload,
            headers={"Content-Type": "application/json"},
        )

    @task(2)
    def send_booking_request(self):
        """Simulate booking request message."""
        booking_texts = list(BOOKING_MESSAGES.values())
        payload = create_webhook_payload(
            phone=self.phone,
            text=random.choice(booking_texts),
            message_id=f"wamid.booking_{self.phone}_{self.message_counter}",
        )
        self.message_counter += 1

        self.client.post(
            "/webhook",
            json=payload,
            headers={"Content-Type": "application/json"},
        )

    @task(1)
    def send_name_introduction(self):
        """Simulate name introduction message."""
        names = list(NAME_MESSAGES.values())
        payload = create_webhook_payload(
            phone=self.phone,
            text=random.choice(names),
            message_id=f"wamid.name_{self.phone}_{self.message_counter}",
        )
        self.message_counter += 1

        self.client.post(
            "/webhook",
            json=payload,
            headers={"Content-Type": "application/json"},
        )

    @task(1)
    def send_email(self):
        """Simulate email provision."""
        emails = [
            "Meine Email ist test@example.de",
            "Email: max.mustermann@gmail.com",
            "Erreichbar unter anna@web.de",
        ]
        payload = create_webhook_payload(
            phone=self.phone,
            text=random.choice(emails),
            message_id=f"wamid.email_{self.phone}_{self.message_counter}",
        )
        self.message_counter += 1

        self.client.post(
            "/webhook",
            json=payload,
            headers={"Content-Type": "application/json"},
        )


class WebhookVerificationUser(HttpUser):
    """Simulates webhook verification requests (less frequent)."""

    wait_time = between(10, 30)  # Less frequent than message users

    @task
    def verify_webhook(self):
        """Verify webhook endpoint."""
        self.client.get(
            "/webhook",
            params={
                "hub.verify_token": "test_verify_token",
                "hub.challenge": f"challenge_{random.randint(1000, 9999)}",
            },
        )


class MixedTrafficUser(HttpUser):
    """Simulates mixed traffic patterns."""

    wait_time = between(0.5, 2)

    def on_start(self):
        """Initialize user session."""
        self.phone = f"49{random.randint(1000000000, 9999999999)}"
        self.message_counter = 0
        self.conversation_stage = 0  # Track conversation progress

    @task(10)
    def realistic_conversation(self):
        """Simulate realistic conversation flow."""
        stages = [
            "Hallo!",
            "Was kostet das Training?",
            "Ich bin Max Mustermann",
            "Meine Email ist max@test.de",
            "Beratungstermin am 20.01. um 14 Uhr",
        ]

        if self.conversation_stage < len(stages):
            text = stages[self.conversation_stage]
            self.conversation_stage += 1
        else:
            # Reset for new conversation
            self.conversation_stage = 0
            self.phone = f"49{random.randint(1000000000, 9999999999)}"
            text = stages[0]

        payload = create_webhook_payload(
            phone=self.phone,
            text=text,
            message_id=f"wamid.conv_{self.phone}_{self.message_counter}",
        )
        self.message_counter += 1

        self.client.post(
            "/webhook",
            json=payload,
            headers={"Content-Type": "application/json"},
        )


# Quick stress test configuration
class StressTestUser(HttpUser):
    """High-frequency user for stress testing."""

    wait_time = between(0.1, 0.5)  # Very fast requests

    def on_start(self):
        """Initialize stress test user."""
        self.counter = 0

    @task
    def rapid_messages(self):
        """Send messages rapidly."""
        payload = create_webhook_payload(
            phone=f"49{random.randint(1000000000, 9999999999)}",
            text="Stress test message",
            message_id=f"wamid.stress_{self.counter}",
        )
        self.counter += 1

        self.client.post(
            "/webhook",
            json=payload,
            headers={"Content-Type": "application/json"},
        )
