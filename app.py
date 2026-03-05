import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from flask import Flask, request, jsonify

app = Flask(__name__)

# ── Attach CORS headers to EVERY response ────────────
# No flask-cors needed — this runs after every request.
@app.after_request
def add_cors_headers(response):
    response.headers['Access-Control-Allow-Origin']  = '*'
    response.headers['Access-Control-Allow-Methods'] = 'POST, OPTIONS, GET'
    response.headers['Access-Control-Allow-Headers'] = 'Content-Type'
    return response


# ── Health check — UptimeRobot pings this ─────────────
@app.route('/', methods=['GET'])
def health():
    return jsonify({'status': 'ZULFR backend nominal'}), 200


# ── CORS preflight for /send ──────────────────────────
@app.route('/send', methods=['OPTIONS'])
def send_preflight():
    return jsonify({}), 200


# ── Main inquiry endpoint ─────────────────────────────
@app.route('/send', methods=['POST'])
def send():
    data = request.get_json(silent=True)
    if not data:
        return jsonify({'error': 'Invalid request body.'}), 400

    name    = data.get('name',    '').strip()
    org     = data.get('org',     '').strip()
    email   = data.get('email',   '').strip()
    inquiry = data.get('type',    'Not specified').strip()
    message = data.get('message', '').strip()

    if not name or not email:
        return jsonify({'error': 'Name and email are required.'}), 422

    subject = 'ZULFR Inquiry — ' + inquiry
    body = (
        'New inquiry received via zulfr.com\n\n'
        'Name:         ' + name + '\n'
        'Organization: ' + (org or '—') + '\n'
        'Email:        ' + email + '\n'
        'Type:         ' + inquiry + '\n\n'
        'Message:\n' + (message or '—') + '\n'
    )

    msg = MIMEMultipart()
    msg['From']     = os.environ['SMTP_USER']
    msg['To']       = os.environ['SMTP_USER']
    msg['Subject']  = subject
    msg['Reply-To'] = email
    msg.attach(MIMEText(body, 'plain'))

    try:
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
            server.login(os.environ['SMTP_USER'], os.environ['SMTP_PASS'])
            server.sendmail(
                os.environ['SMTP_USER'],
                os.environ['SMTP_USER'],
                msg.as_string()
            )
        return jsonify({'status': 'sent'}), 200

    except smtplib.SMTPAuthenticationError:
        return jsonify({'error': 'SMTP auth failed. Use a Gmail App Password, not your login password.'}), 500

    except KeyError as e:
        return jsonify({'error': 'Missing environment variable: ' + str(e)}), 500

    except Exception as e:
        return jsonify({'error': 'Failed to send: ' + str(e)}), 500


if __name__ == '__main__':
    app.run()
