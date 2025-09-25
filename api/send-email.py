import os
import json
import smtplib
from email.mime.text import MIMEText

def handler(request):
    # Δέχομαστε μόνο POST
    if request.method != "POST":
        return {
            "statusCode": 405,
            "headers": {"Allow": "POST", "Content-Type": "application/json"},
            "body": json.dumps({"error": "Method Not Allowed"})
        }

    # Προαιρετικός έλεγχος secret (προτείνεται)
    expected_secret = os.environ.get("WEBHOOK_SECRET")
    provided = request.headers.get("x-webhook-secret") or request.args.get("secret") or (request.json() or {}).get("secret")
    if expected_secret and provided != expected_secret:
        return {
            "statusCode": 401,
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps({"error": "Unauthorized (invalid secret)"})
        }

    try:
        data = request.json() or {}
    except Exception as e:
        # αν το body δεν είναι json
        return {
            "statusCode": 400,
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps({"error": "Invalid JSON body", "detail": str(e)})
        }

    to = data.get("to")
    subject = data.get("subject", "(no subject)")
    text = data.get("text", "")
    html = data.get("html")  # προαιρετικό

    if not to or (not text and not html):
        return {
            "statusCode": 400,
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps({"error": "Missing required fields: to and (text|html)"})
        }

    # SMTP config from env
    smtp_host = os.environ.get("SMTP_HOST", "smtp.gmail.com")
    smtp_port = int(os.environ.get("SMTP_PORT", "587"))
    smtp_secure = os.environ.get("SMTP_SECURE", "false").lower() == "true"  # true αν 465
    smtp_user = os.environ.get("SMTP_USER")
    smtp_pass = os.environ.get("SMTP_PASS")
    from_email = os.environ.get("FROM_EMAIL") or smtp_user

    if not smtp_user or not smtp_pass:
        return {
            "statusCode": 500,
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps({"error": "SMTP credentials not set in environment variables"})
        }

    try:
        # Προετοιμασία μηνύματος (αν υπάρχει html προτιμάται)
        if html:
            msg = MIMEText(html, "html")
        else:
            msg = MIMEText(text, "plain")

        msg["Subject"] = subject
        msg["From"] = from_email
        msg["To"] = to

        # Σύνδεση SMTP
        if smtp_secure and smtp_port == 465:
            server = smtplib.SMTP_SSL(smtp_host, smtp_port, timeout=30)
        else:
            server = smtplib.SMTP(smtp_host, smtp_port, timeout=30)
            server.ehlo()
            if smtp_port == 587:
                server.starttls()
                server.ehlo()

        server.login(smtp_user, smtp_pass)
        server.sendmail(from_email, [to], msg.as_string())
        server.quit()

        return {
            "statusCode": 200,
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps({"success": True, "to": to})
        }

    except Exception as e:
        # log (Vercel θα εμφανίσει αυτά στα logs)
        print("send_email error:", str(e))
        return {
            "statusCode": 500,
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps({"error": "Failed to send email", "detail": str(e)})
        }
