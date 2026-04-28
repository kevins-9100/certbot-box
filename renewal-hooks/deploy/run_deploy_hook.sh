#!/bin/bash
whoami >> /var/log/certbot-user.log 2>&1
# This script is a secure wrapper for the Certbot deployment hook.
# It sources the environment variable file to load the API key,
# ensuring the key is never exposed in the crontab.
# Define the path to your secrets file.
SECRETS_FILE="/etc/letsencrypt/credentials/certbot_secrets.sh"
# Source the secrets file to load the API key.
# The 'source' command is a shell built-in that executes the file's content
# in the current shell, making the environment variable available.
if [ -f "$SECRETS_FILE" ]; then
source "$SECRETS_FILE"
else
echo "ERROR: Secrets file not found at $SECRETS_FILE. Aborting." >&2
exit 1
fi
# Execute the main Certbot deployment hook script.
# The API key is now available in the environment for the Python script.
/etc/letsencrypt/certrenewals.py "$@"
