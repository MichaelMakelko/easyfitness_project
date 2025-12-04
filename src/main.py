# main.py
from whatsapp.webhook import webhook_bp
from flask import Flask

app = Flask(__name__)
app.register_blueprint(webhook_bp)

if __name__ == "__main__":
    print("easyfitness WhatsApp Bot läuft auf http://localhost:5000")
    print("ngrok http 5000 starten und Webhook eintragen!")
    app.run(port=5000, debug=False)