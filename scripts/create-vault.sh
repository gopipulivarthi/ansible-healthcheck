#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."
VAULT_FILE="group_vars/all/vault.yml"
if [[ -e "$VAULT_FILE" ]]; then
  echo "Refusing to overwrite existing $VAULT_FILE" >&2
  exit 1
fi
cp group_vars/all/vault.yml.example "$VAULT_FILE"
chmod 600 "$VAULT_FILE"
echo "Encrypting the lab credentials. Choose a vault password and keep it safe."
/opt/healthcheck/venv/bin/ansible-vault encrypt "$VAULT_FILE"
echo "Encrypted file created: $VAULT_FILE"
echo "Commit the encrypted file to GitHub; never commit a plaintext secrets file."
