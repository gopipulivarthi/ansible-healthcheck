#!/usr/bin/env bash
set -euo pipefail

export DEBIAN_FRONTEND=noninteractive
apt-get update
apt-get install -y \
  ca-certificates curl gnupg git unzip \
  fontconfig openjdk-21-jre \
  python3 python3-venv python3-pip \
  sshpass build-essential

# Install Jenkins LTS using the official Debian/Ubuntu package repository.
install -d -m 0755 /etc/apt/keyrings
curl -fsSL https://pkg.jenkins.io/debian-stable/jenkins.io-2026.key \
  -o /etc/apt/keyrings/jenkins-keyring.asc
chmod 0644 /etc/apt/keyrings/jenkins-keyring.asc
printf '%s\n' \
  'deb [signed-by=/etc/apt/keyrings/jenkins-keyring.asc] https://pkg.jenkins.io/debian-stable binary/' \
  > /etc/apt/sources.list.d/jenkins.list
apt-get update
apt-get install -y jenkins

# Shared Python environment for Ansible, WinRM and the Flask dashboard.
install -d -o root -g root /opt/healthcheck
python3 -m venv /opt/healthcheck/venv
/opt/healthcheck/venv/bin/pip install --upgrade pip
/opt/healthcheck/venv/bin/pip install ansible-core pywinrm Flask

# Jenkins and the vagrant account share the published report directory.
getent group healthcheck >/dev/null || groupadd healthcheck
usermod -aG healthcheck vagrant
usermod -aG healthcheck jenkins
install -d -o vagrant -g healthcheck -m 2775 /var/lib/healthcheck/reports

systemctl enable jenkins
systemctl restart jenkins

cat <<'INFO'

Controller bootstrap completed.
Installed: Java 21, Jenkins, Ansible Core, pywinrm, Flask, Git and sshpass.
Jenkins initial password: sudo cat /var/lib/jenkins/secrets/initialAdminPassword
Jenkins URL: http://192.168.56.10:8080

INFO
