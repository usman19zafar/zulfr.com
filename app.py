from flask import Flask, request
import smtplib
from email.message import EmailMessage
import os

app = Flask(__name__)

@app.post("/send")
def send():
    msg = EmailMessage()
    msg["Subject"] = "New Contact Form Message"
    msg["From"] = request.form["email"]
    msg["To"] = os.getenv("SMTP_USER")
    msg.set_content(request.form["message"])

    with smtplib.SMTP("smtp.gmail.com", 587) as smtp:
        smtp.starttls()
        smtp.login(os.getenv("SMTP_USER"), os.getenv("SMTP_PASS"))
        smtp.send_message(msg)

    return "Message sent"
