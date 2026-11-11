#!/usr/bin/env bash
set -euo pipefail

# Lab-only: enable password authentication for Ansible over the private
# VirtualBox host-only network. The account is the standard Vagrant account.
printf '%s:%s\n' 'vagrant' 'vagrant' | chpasswd
cat > /etc/ssh/sshd_config.d/99-healthcheck-lab.conf <<'SSHCONF'
PasswordAuthentication yes
SSHCONF
sshd -t
systemctl restart ssh
