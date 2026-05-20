 Here are the installation instructions:

  ---
  Installing the Certbot Dashboard

  Prerequisites

  - Ubuntu server with certbot already deployed to /etc/letsencrypt/
  - Python 3 and pip installed
  - Run all commands as root (or with sudo)

  ---
  1. Pull the latest code

  If you clone fresh:
  git clone https://github.com/kevins-9100/cerbot-v2.git /tmp/certbot-v2
  cd /tmp/certbot-v2

  If you already have the repo:
  cd /path/to/certbot-v2
  git pull

  ---
  2. Run the install script

  sudo bash install_certdash.sh

  This will:
  - Install the flask Python package
  - Copy certdash.py to /etc/letsencrypt/certdash.py
  - Install and enable the certdash systemd service
  - Start the web server immediately

  ---
  3. Verify it's running

  systemctl status certdash

  You should see active (running). Then open a browser and navigate to:

  http://<server-ip>:5000

  ---
  Useful commands

  ┌─────────────────────┬────────────────────────────┐
  │       Action        │          Command           │
  ├─────────────────────┼────────────────────────────┤
  │ View live logs      │ journalctl -u certdash -f  │
  ├─────────────────────┼────────────────────────────┤
  │ Restart the service │ systemctl restart certdash │
  ├─────────────────────┼────────────────────────────┤
  │ Stop the service    │ systemctl stop certdash    │
  ├─────────────────────┼────────────────────────────┤
  │ Disable on boot     │ systemctl disable certdash │
  └─────────────────────┴────────────────────────────┘

  ---
  Notes

  - The dashboard auto-refreshes every 60 seconds.
  - The service runs as root so it can read certificates in /etc/letsencrypt/live/.
  - The service starts automatically on server reboot.
  - If port 5000 is blocked by a firewall, allow it with: ufw allow 5000/tcp
