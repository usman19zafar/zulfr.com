import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

from flask import Flask, request, jsonify
from flask_cors import CORS

app = Flask(__name__)

# ── Allow requests from your live site only ──────────
CORS(app, origins=["https://zulfr.com", "https://www.zulfr.com"])

@app.route("/send", methods=["POST", "OPTIONS"])
def send():
    # Browser sends an OPTIONS preflight before the real POST — handle it
    if request.method == "OPTIONS":
        return jsonify({}), 200

    data = request.get_json(silent=True)
    if not data:
        return jsonify({"error": "Invalid request body."}), 400

    name    = data.get("name", "").strip()
    org     = data.get("org", "").strip()
    email   = data.get("email", "").strip()
    inquiry = data.get("type", "Not specified").strip()
    message = data.get("message", "").strip()

    if not name or not email:
        return jsonify({"error": "Name and email are required."}), 422

    # ── Build the email ───────────────────────────────
    subject = f"ZULFR Inquiry — {inquiry}"
    body = f"""New inquiry received via zulfr.com

Name:         {name}
Organization: {org or "—"}
Email:        {email}
Type:         {inquiry}

Message:
{message or "—"}
"""

    msg = MIMEMultipart()
    msg["From"]    = os.environ["SMTP_USER"]
    msg["To"]      = os.environ["SMTP_USER"]   # sends to yourself
    msg["Subject"] = subject
    msg["Reply-To"] = email                    # reply goes directly to sender
    msg.attach(MIMEText(body, "plain"))

    # ── Send via Gmail SMTP ───────────────────────────
    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(os.environ["SMTP_USER"], os.environ["SMTP_PASS"])
            server.sendmail(os.environ["SMTP_USER"], os.environ["SMTP_USER"], msg.as_string())
        return jsonify({"status": "sent"}), 200

    except smtplib.SMTPAuthenticationError:
        return jsonify({"error": "Email authentication failed. Check SMTP credentials."}), 500
    except Exception as e:
        return jsonify({"error": f"Failed to send: {str(e)}"}), 500


if __name__ == "__main__":
    app.run()
