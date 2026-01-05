# main.py
"""Easyfitness WhatsApp Bot - Entry point."""

from flask import Flask

from api.routes import webhook_bp

app = Flask(__name__)
app.register_blueprint(webhook_bp)

if __name__ == "__main__":
    print("easyfitness WhatsApp Bot läuft auf http://localhost:5000")
    print("ngrok http 5000 starten und Webhook eintragen!")
    app.run(port=5000, debug=False)
