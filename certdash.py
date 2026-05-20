#!/usr/bin/env python3

import os
import json
import subprocess
from datetime import datetime, timezone
from flask import Flask, request, redirect, url_for, flash, get_flashed_messages
from jinja2 import Environment, DictLoader
from OpenSSL import crypto

# ── config ────────────────────────────────────────────────────────────────────

LIVE_DIR = "/etc/letsencrypt/live"
IIS_MAP_FILE = "/etc/letsencrypt/iis_cert_map.json"
PANORAMA_MAP_FILE = "/etc/letsencrypt/panorama_cert_map.json"
EMAIL_CONFIG_FILE = "/etc/letsencrypt/emailserver.json"
RENEW_BEFORE_EXPIRY_DAYS = 30
PORT = 5000
ACME_STAGING = "https://acme-staging-v02.api.letsencrypt.org/directory"

app = Flask(__name__)
app.secret_key = "certdash-2024"

# ── helpers ───────────────────────────────────────────────────────────────────

def load_json(path):
    with open(path) as f:
        return json.load(f)

def save_json(path, data):
    with open(path, "w") as f:
        json.dump(data, f, indent=2)

def get_sender_email():
    try:
        return load_json(EMAIL_CONFIG_FILE)["SENDER_EMAIL"]
    except Exception:
        return "certbot@localhost"

def get_cert_info():
    certs = []
    if not os.path.isdir(LIVE_DIR):
        return certs
    now = datetime.now(tz=timezone.utc)
    for cert_name in sorted(os.listdir(LIVE_DIR)):
        cert_path = os.path.join(LIVE_DIR, cert_name, "cert.pem")
        if not os.path.isfile(cert_path):
            continue
        try:
            with open(cert_path, "rb") as f:
                cert = crypto.load_certificate(crypto.FILETYPE_PEM, f.read())
            expiry_str = cert.get_notAfter().decode("ascii")
            expiry = datetime.strptime(expiry_str, "%Y%m%d%H%M%SZ").replace(tzinfo=timezone.utc)
            days_expiry = (expiry - now).days
            days_renewal = days_expiry - RENEW_BEFORE_EXPIRY_DAYS
            if days_expiry > RENEW_BEFORE_EXPIRY_DAYS:
                status, label = "ok", "Healthy"
            elif days_expiry > 14:
                status, label = "warning", "Renewing Soon"
            else:
                status, label = "critical", "Critical"
            certs.append({
                "name": cert_name,
                "expiry": expiry.strftime("%Y-%m-%d %H:%M UTC"),
                "days_expiry": days_expiry,
                "days_renewal": days_renewal,
                "status": status,
                "status_label": label,
                "error": None,
            })
        except Exception as e:
            certs.append({"name": cert_name, "error": str(e), "status": "error"})
    return certs

# ── templates ─────────────────────────────────────────────────────────────────

_BASE = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width,initial-scale=1">
  {% if refresh %}<meta http-equiv="refresh" content="{{ refresh }}">{% endif %}
  <title>Certbot — {{ title }}</title>
  <style>
    *{box-sizing:border-box;margin:0;padding:0}
    body{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;background:#0f172a;color:#e2e8f0;min-height:100vh}
    nav{background:#1e293b;border-bottom:1px solid #334155;padding:0 2rem;display:flex;align-items:center;gap:.25rem}
    .brand{font-weight:700;color:#f1f5f9;margin-right:1.5rem;padding:1rem 0}
    nav a{color:#94a3b8;text-decoration:none;padding:1rem .75rem;font-size:.875rem;border-bottom:2px solid transparent;display:inline-block}
    nav a:hover{color:#f1f5f9}
    nav a.active{color:#38bdf8;border-bottom-color:#38bdf8}
    .page{padding:2rem;max-width:1100px}
    h2{font-size:1.25rem;font-weight:600;margin-bottom:1.5rem}
    h3{font-size:.75rem;font-weight:600;color:#64748b;text-transform:uppercase;letter-spacing:.05em;margin-bottom:.75rem}
    table{width:100%;border-collapse:collapse;background:#1e293b;border-radius:.75rem;overflow:hidden;margin-bottom:1.5rem}
    th{background:#0f172a;padding:.75rem 1rem;text-align:left;font-size:.75rem;text-transform:uppercase;letter-spacing:.05em;color:#64748b}
    td{padding:.75rem 1rem;border-top:1px solid #334155;font-size:.875rem;vertical-align:middle}
    tr:hover td{background:#273548}
    .badge{display:inline-block;padding:.2rem .6rem;border-radius:9999px;font-size:.75rem;font-weight:600}
    .ok{background:#14532d;color:#4ade80}
    .warning{background:#713f12;color:#facc15}
    .critical{background:#7f1d1d;color:#f87171}
    .err-b{background:#1e1b4b;color:#818cf8}
    .num{font-size:1.25rem;font-weight:700}
    .lbl{color:#64748b;font-size:.75rem}
    .ra{color:#facc15}
    .ro{color:#4ade80}
    .card{background:#1e293b;border-radius:.75rem;padding:1.5rem;margin-bottom:1.5rem}
    .row{display:flex;gap:.75rem;flex-wrap:wrap;align-items:flex-end;margin-bottom:.75rem}
    .field{display:flex;flex-direction:column;gap:.3rem}
    label{font-size:.75rem;color:#94a3b8;text-transform:uppercase;letter-spacing:.05em}
    input[type=text],select{background:#0f172a;border:1px solid #334155;color:#e2e8f0;padding:.5rem .75rem;border-radius:.375rem;font-size:.875rem;min-width:160px}
    input.wide{min-width:280px}
    input:focus,select:focus{outline:none;border-color:#38bdf8}
    .btn{background:#1d4ed8;color:#fff;border:none;padding:.5rem 1rem;border-radius:.375rem;font-size:.875rem;cursor:pointer;font-weight:500}
    .btn:hover{background:#2563eb}
    .btn-d{background:#991b1b}.btn-d:hover{background:#dc2626}
    .btn-s{background:#334155;color:#e2e8f0;border:none;padding:.5rem 1rem;border-radius:.375rem;font-size:.875rem;cursor:pointer;font-weight:500}
    .btn-s:hover{background:#475569}
    .flash{padding:.75rem 1rem;border-radius:.5rem;margin-bottom:1.5rem;font-size:.875rem}
    .fs{background:#14532d;color:#4ade80}
    .fe{background:#7f1d1d;color:#f87171}
    .output{background:#020617;border:1px solid #1e293b;border-radius:.5rem;padding:1rem;font-family:monospace;font-size:.8rem;white-space:pre-wrap;color:#94a3b8;max-height:420px;overflow-y:auto;margin-top:1rem}
    .mono{font-family:monospace;font-size:.875rem;color:#94a3b8}
    hr{border:none;border-top:1px solid #334155;margin:1.5rem 0}
    .hint{font-size:.75rem;color:#64748b;margin-top:.3rem}
    .footer{font-size:.75rem;color:#475569;text-align:right;margin-top:.5rem}
  </style>
</head>
<body>
  <nav>
    <span class="brand">Certbot</span>
    <a href="{{ url_for('dashboard') }}"{% if active=='dashboard' %} class="active"{% endif %}>Dashboard</a>
    <a href="{{ url_for('register') }}"{% if active=='register' %} class="active"{% endif %}>Register Cert</a>
    <a href="{{ url_for('iis_page') }}"{% if active=='iis' %} class="active"{% endif %}>IIS Mappings</a>
    <a href="{{ url_for('panorama_page') }}"{% if active=='panorama' %} class="active"{% endif %}>Panorama Mappings</a>
  </nav>
  <div class="page">
    {% for cat, msg in messages %}
    <div class="flash {{ 'fs' if cat=='success' else 'fe' }}">{{ msg }}</div>
    {% endfor %}
    {% block content %}{% endblock %}
  </div>
</body>
</html>"""

_DASHBOARD = """{% extends 'base.html' %}
{% block content %}
<h2>Certificate Dashboard</h2>
<p style="color:#94a3b8;font-size:.875rem;margin-bottom:1.5rem">
  Auto-refreshes every 60 seconds &mdash; Last updated: {{ last_updated }}
</p>
<table>
  <thead>
    <tr>
      <th>Domain</th><th>Status</th><th>Expiry Date</th>
      <th>Days Until Expiry</th><th>Days Until Auto-Renewal</th>
    </tr>
  </thead>
  <tbody>
    {% for c in certs %}
      {% if c.error %}
      <tr>
        <td class="mono">{{ c.name }}</td>
        <td><span class="badge err-b">Error</span></td>
        <td colspan="3" style="color:#94a3b8">{{ c.error }}</td>
      </tr>
      {% else %}
      <tr>
        <td class="mono">{{ c.name }}</td>
        <td><span class="badge {{ c.status }}">{{ c.status_label }}</span></td>
        <td>{{ c.expiry }}</td>
        <td><span class="num">{{ c.days_expiry }}</span> <span class="lbl">days</span></td>
        <td>
          {% if c.days_renewal <= 0 %}
            <span class="num ra">&mdash;</span>
            <span class="lbl">renewal in progress</span>
          {% else %}
            <span class="num ro">{{ c.days_renewal }}</span>
            <span class="lbl">days</span>
          {% endif %}
        </td>
      </tr>
      {% endif %}
    {% else %}
    <tr>
      <td colspan="5" style="text-align:center;color:#64748b;padding:2rem">
        No certificates found in {{ live_dir }}
      </td>
    </tr>
    {% endfor %}
  </tbody>
</table>
<p class="footer">
  Reading from {{ live_dir }} &bull; Certbot renews {{ renew_days }} days before expiry
</p>
{% endblock %}"""

_REGISTER = """{% extends 'base.html' %}
{% block content %}
<h2>Register New Certificate</h2>

<div class="card">
  <h3>Step 1 &mdash; Register Domain with ACME DNS</h3>
  <p class="hint" style="margin-bottom:1rem">
    Creates a CNAME record in the acme-dns server. You must add the resulting CNAME to your
    public DNS before issuing the certificate.
  </p>
  <form method="POST" onsubmit="lock(this,'Registering…')">
    <input type="hidden" name="action" value="register-acme">
    <div class="row">
      <div class="field">
        <label>Domain</label>
        <input type="text" name="domain" placeholder="example.com" required value="{{ domain or '' }}" class="wide">
      </div>
      <div class="field">
        <label>ACME DNS Server</label>
        <input type="text" name="acme_server" value="{{ acme_server or 'http://localhost:8080' }}" class="wide">
      </div>
      <div class="field" style="justify-content:flex-end">
        <button type="submit" class="btn-s">Register with ACME DNS</button>
      </div>
    </div>
  </form>
  {% if action == 'register-acme' and output is not none %}
  <hr>
  <h3>Output</h3>
  <div class="output">{{ output }}</div>
  <p class="hint" style="margin-top:.75rem;color:#facc15">
    &#9888; Add the CNAME record shown above to your DNS provider, then proceed to Step 2.
  </p>
  {% endif %}
</div>

<div class="card">
  <h3>Step 2 &mdash; Issue Certificate</h3>
  <p class="hint" style="margin-bottom:1rem">
    Runs certbot with acme-dns-client as the DNS-01 auth hook. Complete Step 1 and
    add the CNAME first.
  </p>
  <form method="POST" onsubmit="lock(this,'Issuing…')">
    <input type="hidden" name="action" value="issue-cert">
    <div class="row">
      <div class="field">
        <label>Domain</label>
        <input type="text" name="domain" placeholder="example.com" required value="{{ domain or '' }}" class="wide">
      </div>
      <div class="field">
        <label>Environment</label>
        <select name="env">
          <option value="production"{% if (env or 'production')=='production' %} selected{% endif %}>Production (Let&apos;s Encrypt)</option>
          <option value="staging"{% if env=='staging' %} selected{% endif %}>Staging (Test)</option>
        </select>
      </div>
      <div class="field" style="justify-content:flex-end">
        <button type="submit" class="btn">Issue Certificate</button>
        <p class="hint">May take up to 2 minutes</p>
      </div>
    </div>
  </form>
  {% if action == 'issue-cert' and output is not none %}
  <hr>
  <h3>Certbot Output</h3>
  <div class="output">{{ output }}</div>
  {% endif %}
</div>

<script>
function lock(form, label) {
  var btn = form.querySelector('button[type=submit]');
  btn.textContent = label;
  btn.disabled = true;
}
</script>
{% endblock %}"""

_IIS = """{% extends 'base.html' %}
{% block content %}
<h2>IIS Certificate Mappings</h2>

<div class="card">
  <h3>SSH Defaults</h3>
  <form method="POST" action="{{ url_for('iis_update_defaults') }}">
    <div class="row">
      <div class="field">
        <label>Username</label>
        <input type="text" name="username" value="{{ defaults.get('username', '') }}">
      </div>
      <div class="field">
        <label>SSH Key Path</label>
        <input type="text" name="ssh_key_path" value="{{ defaults.get('ssh_key_path', '') }}" class="wide">
      </div>
      <div class="field" style="justify-content:flex-end">
        <button class="btn-s">Update Defaults</button>
      </div>
    </div>
  </form>
</div>

{% if mappings %}
<div class="card">
  <h3>Current Mappings</h3>
  <table>
    <thead>
      <tr>
        <th>Cert Name</th><th>Server</th><th>Website Name</th><th>IP Address</th><th></th>
      </tr>
    </thead>
    <tbody>
      {% for cert_name, servers in mappings.items() %}
        {% for srv in servers %}
        <tr>
          <td class="mono">{% if loop.first %}{{ cert_name }}{% endif %}</td>
          <td class="mono">{{ srv.server }}</td>
          <td>{{ srv.website_name }}</td>
          <td class="mono">{{ srv.ip_address }}</td>
          <td>
            <form method="POST" action="{{ url_for('iis_delete') }}" style="margin:0">
              <input type="hidden" name="cert_name" value="{{ cert_name }}">
              <input type="hidden" name="idx" value="{{ loop.index0 }}">
              <button class="btn btn-d" onclick="return confirm('Delete this entry?')">Delete</button>
            </form>
          </td>
        </tr>
        {% endfor %}
      {% endfor %}
    </tbody>
  </table>
</div>
{% endif %}

<div class="card">
  <h3>Add Mapping</h3>
  <form method="POST" action="{{ url_for('iis_add') }}">
    <div class="row">
      <div class="field">
        <label>Cert Name</label>
        <input type="text" name="cert_name" placeholder="example.com">
      </div>
      <div class="field">
        <label>Server IP</label>
        <input type="text" name="server" placeholder="192.168.1.10">
      </div>
      <div class="field">
        <label>Website Name</label>
        <input type="text" name="website_name" placeholder="Default Web Site">
      </div>
      <div class="field">
        <label>IP Address</label>
        <input type="text" name="ip_address" placeholder="192.168.1.10">
      </div>
      <div class="field" style="justify-content:flex-end">
        <button class="btn">Add</button>
      </div>
    </div>
  </form>
</div>
{% endblock %}"""

_PANORAMA = """{% extends 'base.html' %}
{% block content %}
<h2>Panorama Certificate Mappings</h2>

<div class="card">
  <h3>Panorama Connection</h3>
  <form method="POST" action="{{ url_for('panorama_update_ip') }}">
    <div class="row">
      <div class="field">
        <label>Panorama IP</label>
        <input type="text" name="panorama_ip" value="{{ panorama_ip }}">
      </div>
      <div class="field" style="justify-content:flex-end">
        <button class="btn-s">Update IP</button>
      </div>
    </div>
  </form>
</div>

{% if deployments %}
<div class="card">
  <h3>Certificate Deployments</h3>
  <table>
    <thead>
      <tr>
        <th>Cert Name</th><th>Panorama Name</th><th>Device Group</th><th>Template</th><th></th>
      </tr>
    </thead>
    <tbody>
      {% for cert_name, dep in deployments.items() %}
      <tr>
        <td class="mono">{{ cert_name }}</td>
        <td class="mono">{{ dep.panorama_name }}</td>
        <td>{{ dep.target_dg or '(shared)' }}</td>
        <td>{{ dep.target_tpl or '(shared)' }}</td>
        <td>
          <form method="POST" action="{{ url_for('panorama_delete') }}" style="margin:0">
            <input type="hidden" name="cert_name" value="{{ cert_name }}">
            <button class="btn btn-d" onclick="return confirm('Delete this deployment?')">Delete</button>
          </form>
        </td>
      </tr>
      {% endfor %}
    </tbody>
  </table>
</div>
{% endif %}

<div class="card">
  <h3>Add Deployment</h3>
  <form method="POST" action="{{ url_for('panorama_add') }}">
    <div class="row">
      <div class="field">
        <label>Cert Name</label>
        <input type="text" name="cert_name" placeholder="example.com">
      </div>
      <div class="field">
        <label>Panorama Name</label>
        <input type="text" name="panorama_name" placeholder="example_com">
      </div>
      <div class="field">
        <label>Device Group</label>
        <input type="text" name="target_dg" placeholder="leave blank for shared">
      </div>
      <div class="field">
        <label>Template</label>
        <input type="text" name="target_tpl" placeholder="leave blank for shared">
      </div>
      <div class="field" style="justify-content:flex-end">
        <button class="btn">Add</button>
      </div>
    </div>
  </form>
</div>
{% endblock %}"""

# ── jinja2 environment ────────────────────────────────────────────────────────

_jinja = Environment(
    loader=DictLoader({
        "base.html": _BASE,
        "dashboard.html": _DASHBOARD,
        "register.html": _REGISTER,
        "iis.html": _IIS,
        "panorama.html": _PANORAMA,
    }),
    autoescape=True,
)


def render(tpl, active, title, refresh=None, **kw):
    return _jinja.get_template(tpl).render(
        url_for=url_for,
        messages=get_flashed_messages(with_categories=True),
        active=active,
        title=title,
        refresh=refresh,
        **kw,
    )

# ── routes — dashboard ────────────────────────────────────────────────────────

@app.route("/")
def dashboard():
    return render("dashboard.html", "dashboard", "Dashboard",
        refresh=60,
        certs=get_cert_info(),
        last_updated=datetime.now(tz=timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
        live_dir=LIVE_DIR,
        renew_days=RENEW_BEFORE_EXPIRY_DAYS,
    )

# ── routes — register cert ────────────────────────────────────────────────────

@app.route("/register", methods=["GET", "POST"])
def register():
    output = None
    domain = None
    env = "production"
    action = None
    acme_server = "http://localhost:8080"

    if request.method == "POST":
        action = request.form.get("action", "issue-cert")
        domain = request.form.get("domain", "").strip()
        env = request.form.get("env", "production")
        acme_server = request.form.get("acme_server", "http://localhost:8080").strip()

        if not domain:
            flash("Domain is required.", "error")
        elif action == "register-acme":
            cmd = ["acme-dns-client", "register", "-d", domain, "-s", acme_server]
            try:
                result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
                output = result.stdout
                if result.stderr:
                    output += "\n" + result.stderr
                if result.returncode == 0:
                    flash(f"{domain} registered with ACME DNS. Add the CNAME before issuing.", "success")
                else:
                    flash(f"acme-dns-client exited with code {result.returncode}.", "error")
            except Exception as e:
                output = f"Error: {e}"
                flash("Failed to run acme-dns-client.", "error")
        elif action == "issue-cert":
            cmd = [
                "certbot", "certonly",
                "--non-interactive", "--agree-tos",
                "--email", get_sender_email(),
                "--manual",
                "--preferred-challenges", "dns",
                "--manual-auth-hook", "acme-dns-client",
                "--key-type", "ecdsa",
                "-d", domain,
            ]
            if env == "staging":
                cmd += ["--server", ACME_STAGING]
            try:
                result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
                output = result.stdout
                if result.stderr:
                    output += "\n" + result.stderr
                if result.returncode == 0:
                    flash(f"Certificate for {domain} issued successfully.", "success")
                else:
                    flash(f"Certbot exited with code {result.returncode}.", "error")
            except subprocess.TimeoutExpired:
                output = "Error: certbot timed out after 120 seconds."
                flash("Certbot timed out.", "error")
            except Exception as e:
                output = f"Error running certbot: {e}"
                flash("Failed to run certbot.", "error")

    return render("register.html", "register", "Register Certificate",
        output=output, domain=domain, env=env, action=action, acme_server=acme_server)

# ── routes — IIS mappings ─────────────────────────────────────────────────────

@app.route("/iis")
def iis_page():
    data = load_json(IIS_MAP_FILE)
    return render("iis.html", "iis", "IIS Mappings",
        defaults=data.get("_defaults_", {}),
        mappings={k: v for k, v in data.items() if k != "_defaults_"},
    )


@app.route("/iis/update-defaults", methods=["POST"])
def iis_update_defaults():
    data = load_json(IIS_MAP_FILE)
    data["_defaults_"] = {
        "username": request.form.get("username", "").strip(),
        "ssh_key_path": request.form.get("ssh_key_path", "").strip(),
    }
    save_json(IIS_MAP_FILE, data)
    flash("Defaults updated.", "success")
    return redirect(url_for("iis_page"))


@app.route("/iis/add", methods=["POST"])
def iis_add():
    cert_name = request.form.get("cert_name", "").strip()
    server = request.form.get("server", "").strip()
    website_name = request.form.get("website_name", "").strip()
    ip_address = request.form.get("ip_address", "").strip()

    if not all([cert_name, server, website_name, ip_address]):
        flash("All fields are required.", "error")
        return redirect(url_for("iis_page"))

    data = load_json(IIS_MAP_FILE)
    data.setdefault(cert_name, []).append({
        "server": server,
        "website_name": website_name,
        "ip_address": ip_address,
    })
    save_json(IIS_MAP_FILE, data)
    flash(f"Added IIS mapping for {cert_name}.", "success")
    return redirect(url_for("iis_page"))


@app.route("/iis/delete", methods=["POST"])
def iis_delete():
    cert_name = request.form.get("cert_name", "")
    idx = int(request.form.get("idx", -1))
    data = load_json(IIS_MAP_FILE)
    entries = data.get(cert_name, [])
    if 0 <= idx < len(entries):
        entries.pop(idx)
        if not entries:
            del data[cert_name]
        save_json(IIS_MAP_FILE, data)
        flash(f"Deleted IIS entry for {cert_name}.", "success")
    else:
        flash("Entry not found.", "error")
    return redirect(url_for("iis_page"))

# ── routes — Panorama mappings ────────────────────────────────────────────────

@app.route("/panorama")
def panorama_page():
    data = load_json(PANORAMA_MAP_FILE)
    return render("panorama.html", "panorama", "Panorama Mappings",
        panorama_ip=data.get("PANORAMA_IP", ""),
        deployments=data.get("CERT_DEPLOYMENTS", {}),
    )


@app.route("/panorama/update-ip", methods=["POST"])
def panorama_update_ip():
    data = load_json(PANORAMA_MAP_FILE)
    data["PANORAMA_IP"] = request.form.get("panorama_ip", "").strip()
    save_json(PANORAMA_MAP_FILE, data)
    flash("Panorama IP updated.", "success")
    return redirect(url_for("panorama_page"))


@app.route("/panorama/add", methods=["POST"])
def panorama_add():
    cert_name = request.form.get("cert_name", "").strip()
    panorama_name = request.form.get("panorama_name", "").strip()
    target_dg = request.form.get("target_dg", "").strip()
    target_tpl = request.form.get("target_tpl", "").strip()

    if not cert_name or not panorama_name:
        flash("Cert name and Panorama name are required.", "error")
        return redirect(url_for("panorama_page"))

    data = load_json(PANORAMA_MAP_FILE)
    data.setdefault("CERT_DEPLOYMENTS", {})[cert_name] = {
        "panorama_name": panorama_name,
        "target_dg": target_dg,
        "target_tpl": target_tpl,
    }
    save_json(PANORAMA_MAP_FILE, data)
    flash(f"Added Panorama deployment for {cert_name}.", "success")
    return redirect(url_for("panorama_page"))


@app.route("/panorama/delete", methods=["POST"])
def panorama_delete():
    cert_name = request.form.get("cert_name", "")
    data = load_json(PANORAMA_MAP_FILE)
    if cert_name in data.get("CERT_DEPLOYMENTS", {}):
        del data["CERT_DEPLOYMENTS"][cert_name]
        save_json(PANORAMA_MAP_FILE, data)
        flash(f"Deleted Panorama deployment for {cert_name}.", "success")
    else:
        flash("Deployment not found.", "error")
    return redirect(url_for("panorama_page"))


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=PORT)
