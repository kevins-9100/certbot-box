#!/usr/bin/env python3

import os
import json
import smtplib
import ssl
from datetime import datetime, timezone
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from OpenSSL import crypto

LIVE_DIR = "/etc/letsencrypt/live"
EMAIL_SERVER_CONFIG_FILE = "/etc/letsencrypt/emailserver.json"
RECIPIENTS_CONFIG_FILE = "/etc/letsencrypt/recipients.json"
WARN_DAYS_BEFORE_RENEWAL = 60
RENEW_BEFORE_EXPIRY_DAYS = 30  # match your certbot renew_before_expiry setting
WARN_FLAG_DIR = "/tmp/certbot_expiry_warn"


def load_email_config():
    with open(EMAIL_SERVER_CONFIG_FILE, 'r') as f:
        config = json.load(f)
    return config['SMTP_SERVER'], config['SMTP_PORT'], config['SENDER_EMAIL'], config['SMTP_PASSWORD']


def load_recipients():
    with open(RECIPIENTS_CONFIG_FILE, 'r') as f:
        return json.load(f)


def get_cert_expiry(cert_path):
    with open(cert_path, 'rb') as f:
        cert = crypto.load_certificate(crypto.FILETYPE_PEM, f.read())
    expiry_str = cert.get_notAfter().decode('ascii')
    return datetime.strptime(expiry_str, '%Y%m%d%H%M%SZ').replace(tzinfo=timezone.utc)


def already_warned(cert_name, expiry_date):
    os.makedirs(WARN_FLAG_DIR, exist_ok=True)
    flag_file = os.path.join(WARN_FLAG_DIR, f"{cert_name}_{expiry_date.strftime('%Y%m%d')}.warned")
    return os.path.exists(flag_file)


def mark_warned(cert_name, expiry_date):
    os.makedirs(WARN_FLAG_DIR, exist_ok=True)
    flag_file = os.path.join(WARN_FLAG_DIR, f"{cert_name}_{expiry_date.strftime('%Y%m%d')}.warned")
    open(flag_file, 'w').close()


def send_warning_email(warnings):
    smtp_server, smtp_port, sender_email, smtp_password = load_email_config()
    recipients = load_recipients()

    subject = "Let's Encrypt Certificate Expiry Warning"

    lines = ["The following certificates are approaching their renewal date:\n"]
    for cert_name, days_remaining, expiry_date in warnings:
        lines.append(f"  Certificate : {cert_name}")
        lines.append(f"  Expires     : {expiry_date.strftime('%Y-%m-%d %H:%M UTC')}")
        lines.append(f"  Days left   : {days_remaining}")
        lines.append(f"  Renewal due : in ~{days_remaining - RENEW_BEFORE_EXPIRY_DAYS} days\n")

    lines.append("Certbot should renew these automatically. This is an early warning only.")
    body = "\n".join(lines)

    message = MIMEMultipart("alternative")
    message["Subject"] = subject
    message["From"] = sender_email
    message["To"] = ", ".join(recipients)
    message.attach(MIMEText(body, "plain"))

    with smtplib.SMTP(smtp_server, smtp_port) as server:
        server.ehlo()
        server.starttls()
        server.ehlo()
        server.login(sender_email, smtp_password)
        server.sendmail(sender_email, recipients, message.as_string())

    print(f"Warning email sent to: {', '.join(recipients)}")


def main():
    if not os.path.isdir(LIVE_DIR):
        print(f"ERROR: {LIVE_DIR} not found.")
        return 1

    now = datetime.now(tz=timezone.utc)
    warn_threshold = RENEW_BEFORE_EXPIRY_DAYS + WARN_DAYS_BEFORE_RENEWAL  # 37 days by default
    warnings = []

    for cert_name in sorted(os.listdir(LIVE_DIR)):
        cert_path = os.path.join(LIVE_DIR, cert_name, "cert.pem")
        if not os.path.isfile(cert_path):
            continue

        try:
            expiry = get_cert_expiry(cert_path)
            days_remaining = (expiry - now).days

            print(f"{cert_name}: expires in {days_remaining} days ({expiry.strftime('%Y-%m-%d')})")

            if days_remaining <= warn_threshold:
                if already_warned(cert_name, expiry):
                    print(f"  -> Warning already sent for this expiry. Skipping.")
                else:
                    print(f"  -> Within warning threshold ({warn_threshold} days). Queueing warning.")
                    warnings.append((cert_name, days_remaining, expiry))

        except Exception as e:
            print(f"ERROR reading cert for {cert_name}: {e}")

    if warnings:
        send_warning_email(warnings)
        for cert_name, _, expiry in warnings:
            mark_warned(cert_name, expiry)
    else:
        print("No certificates within warning threshold.")

    return 0


if __name__ == "__main__":
    exit(main())
