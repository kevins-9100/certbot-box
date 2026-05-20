#!/bin/bash
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "==> Installing Flask..."
apt install -y python3-flask

echo "==> Copying files to /etc/letsencrypt/..."
if [ "$(realpath "$SCRIPT_DIR/certdash.py")" != "$(realpath /etc/letsencrypt/certdash.py 2>/dev/null)" ]; then
    cp "$SCRIPT_DIR/certdash.py" /etc/letsencrypt/certdash.py
fi
chmod 700 /etc/letsencrypt/certdash.py

echo "==> Installing systemd service..."
cp "$SCRIPT_DIR/certdash.service" /etc/systemd/system/certdash.service

echo "==> Enabling and starting service..."
systemctl daemon-reload
systemctl enable certdash
systemctl restart certdash

SERVER_IP=$(hostname -I | awk '{print $1}')
echo ""
echo "Done. Dashboard available at: http://${SERVER_IP}:5000"
echo "Logs: journalctl -u certdash -f"
