# Certbot-v2

Let's Encrypt certificate automation for renewing and deploying certificates to Panorama firewalls, IIS servers, and RDS farms.

## Components

| File | Purpose |
|---|---|
| `certrenewals.py` | Main deployment script — pushes renewed certs to Panorama and IIS |
| `cert_expiry_warn.py` | Sends warning emails when certs are within 37 days of expiry |
| `certdash.py` | Web dashboard showing cert status and days until renewal |
| `renewal-hooks/deploy/run_deploy_hook.sh` | Certbot deploy hook — sources secrets and calls `certrenewals.py` |
| `renewal-hooks/post/cert_expiry_warn.sh` | Certbot post hook — calls `cert_expiry_warn.py` |

## Certificate Dashboard

A lightweight Flask web server that displays all certbot-managed certificates, their expiry dates, and days until auto-renewal.

### Install

```bash
sudo bash install_certdash.sh
```

### Access

```
http://<server-ip>:5000
```

The page auto-refreshes every 60 seconds.

### Service management

```bash
sudo systemctl status certdash
sudo systemctl restart certdash
journalctl -u certdash -f
```

## Configuration files

| File | Purpose |
|---|---|
| `panorama_cert_map.json` | Maps cert lineages to Panorama device groups/templates |
| `iis_cert_map.json` | Maps cert lineages to IIS servers and websites |
| `rds_cert_map.json` | Maps cert lineages to RDS farm roles |
| `emailserver.json` | SMTP settings for notification emails |
| `recipients.json` | Email addresses for notifications |
| `credentials/certbot_secrets.sh` | Panorama API key (not committed) |
