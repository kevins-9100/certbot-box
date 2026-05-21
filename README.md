# Certbot-v2

Let's Encrypt certificate automation for renewing and deploying certificates to Panorama firewalls, IIS servers, and RDS farms.

## Components

| File | Purpose |
|---|---|
| `certrenewals.py` | Main deployment script — pushes renewed certs to Panorama and IIS |
| `cert_expiry_warn.py` | Sends warning emails when certs are within 37 days of expiry |
| `certdash.py` | Web dashboard for cert management (see below) |
| `renewal-hooks/deploy/run_deploy_hook.sh` | Certbot deploy hook — sources secrets and calls `certrenewals.py` |
| `renewal-hooks/post/cert_expiry_warn.sh` | Certbot post hook — calls `cert_expiry_warn.py` |

## Certificate Dashboard

A Flask web server that provides full certificate lifecycle management through a browser UI.

### Install

```bash
sudo bash install_certdash.sh
```

This installs `python3-flask`, copies `certdash.py` and `thetalogo.svg` to `/etc/letsencrypt/`, and registers a systemd service that starts automatically on boot.

### Access

```
http://<server-ip>:5000
```

### Pages

| Page | URL | Description |
|---|---|---|
| Dashboard | `/` | All certbot-managed certs with expiry dates, days until expiry, and days until auto-renewal. Auto-refreshes every 60 seconds. |
| Register Cert | `/register` | Two-step cert issuance: Step 1 registers the domain with the local acme-dns server and returns the CNAME record to add to public DNS. Step 2 runs certbot with the acme-dns-client auth hook. Supports SANs and staging environment. |
| IIS Mappings | `/iis` | Edit `iis_cert_map.json` — add/remove IIS server mappings and SSH defaults. |
| Panorama Mappings | `/panorama` | Edit `panorama_cert_map.json` — add/remove Panorama certificate deployments. |
| ACME DNS Accounts | `/acmedns` | Merged view of certbot certs and acme-dns registrations. Shows issue date, CNAME record, and buttons to delete the ACME DNS account or the certificate. |
| Logs | `/logs` | Tail of `/var/log/letsencrypt/letsencrypt.log` with file and line-count selectors. Colour-coded by severity (debug/info/warning/error). |
| Email Settings | `/email` | Edit SMTP configuration and manage notification recipients. |

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
| `/etc/acmedns/clientstorage.json` | acme-dns-client credentials (server file, not in repo) |
