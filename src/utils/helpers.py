# utils/helpers.py
import re
import smtplib
# from email.mime.text import MIMEText
# from config import EMAIL_SENDER, EMAIL_PASSWORD, EMAIL_SMTP_SERVER, EMAIL_SMTP_PORT


def extract_name(text):
    lower = text.lower()
    triggers = ["ich heiße", "mein name ist", "bin der ", "bin die ", "ich bin "]
    for t in triggers:
        if t in lower:
            candidate = lower.split(t)[-1].strip().split()[0].capitalize()
            if 2 <= len(candidate) <= 20 and candidate.lower() not in ["ich", "der", "die", "und"]:
                return candidate
    return None


def extract_booking_intent(text, reply):
    """Erkennt, ob ein Termin vereinbart werden soll (einfach, erweiterbar)"""
    lower_text = text.lower() + reply.lower()
    if "probetraining" in lower_text and "termin" in lower_text and re.search(r'\d{2}\.\d{2}\.\d{4}', lower_text):  # z.B. Datum 12.12.2024
        return True
    return False

def extract_date_time(lower_text):
    """Extrahiert Datum/Uhrzeit aus Text (einfach mit Regex, erweiterbar mit dateparser)"""
    date_match = re.search(r'(\d{2})\.(\d{2})\.(\d{4})', lower_text)
    time_match = re.search(r'(\d{2}):(\d{2})', lower_text)
    if date_match and time_match:
        return f"{date_match.group(3)}-{date_match.group(2)}-{date_match.group(1)}T{time_match.group(1)}:{time_match.group(2)}:00+01:00[Europe/Berlin]"
    return None


# def send_confirmation_email(to_email, name, date_time):
#     """Sendet Bestätigungs-E-Mail"""
#     subject = "Dein Probetraining bei easyfitness EMS"
#     body = f"Hallo {name},\n\ndein Probetraining ist gebucht für {date_time}.\nWir freuen uns auf dich!\n\nDein Team von easyfitness"
    
#     msg = MIMEText(body)
#     msg['Subject'] = subject
#     msg['From'] = EMAIL_SENDER
#     msg['To'] = to_email

#     try:
#         server = smtplib.SMTP(EMAIL_SMTP_SERVER, EMAIL_SMTP_PORT)
#         server.starttls()
#         server.login(EMAIL_SENDER, EMAIL_PASSWORD)
#         server.sendmail(EMAIL_SENDER, to_email, msg.as_string())
#         server.quit()
#         print(f"Bestätigungs-E-Mail gesendet an {to_email}")
#     except Exception as e:
#         print(f"E-Mail-Fehler: {e}")