import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

from flask import Flask, request, jsonify
from flask_cors import CORS

app = Flask(__name__)

# ── CORS — allow all origins so the browser preflight passes ──
# (lock this down to https://zulfr.com once confirmed working)
CORS(app, resources={r"/send": {"origins": "*"}})


@app.route("/", methods=["GET"])
def health():
    """Health check — keeps Render awake via UptimeRobot."""
    return jsonify({"status": "ZULFR backend nominal"}), 200


@app.route("/send", methods=["POST", "OPTIONS"])
def send():
    # Handle CORS preflight manually as a safety net
    if request.method == "OPTIONS":
        response = jsonify({})
        response.headers["Access-Control-Allow-Origin"]  = "*"
        response.headers["Access-Control-Allow-Methods"] = "POST, OPTIONS"
        response.headers["Access-Control-Allow-Headers"] = "Content-Type"
        return response, 200

    data = request.get_json(silent=True)
    if not data:
        return jsonify({"error": "Invalid request body."}), 400

    name    = data.get("name",    "").strip()
    org     = data.get("org",     "").strip()
    email   = data.get("email",   "").strip()
    inquiry = data.get("type",    "Not specified").strip()
    message = data.get("message", "").strip()

    if not name or not email:
        return jsonify({"error": "Name and email are required."}), 422

    # ── Build the email body ───────────────────────────
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
    msg["From"]     = os.environ["SMTP_USER"]
    msg["To"]       = os.environ["SMTP_USER"]
    msg["Subject"]  = subject
    msg["Reply-To"] = email
    msg.attach(MIMEText(body, "plain"))

    # ── Send via Gmail SMTP over SSL ──────────────────
    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(os.environ["SMTP_USER"], os.environ["SMTP_PASS"])
            server.sendmail(
                os.environ["SMTP_USER"],
                os.environ["SMTP_USER"],
                msg.as_string()
            )
        return jsonify({"status": "sent"}), 200

    except smtplib.SMTPAuthenticationError:
        return jsonify({"error": "SMTP authentication failed. Check SMTP_PASS is a Gmail App Password."}), 500

    except KeyError as e:
        return jsonify({"error": f"Missing environment variable: {e}"}), 500

    except Exception as e:
        return jsonify({"error": f"Failed to send: {str(e)}"}), 500


if __name__ == "__main__":
    app.run()
