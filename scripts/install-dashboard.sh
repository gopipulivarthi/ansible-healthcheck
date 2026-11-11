#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
if [[ ! -x /opt/healthcheck/venv/bin/python ]]; then
  echo "Missing /opt/healthcheck/venv. Run the controller bootstrap first." >&2
  exit 1
fi

getent group healthcheck >/dev/null || groupadd healthcheck
usermod -aG healthcheck vagrant
usermod -aG healthcheck jenkins
install -d -o vagrant -g healthcheck -m 2775 /var/lib/healthcheck/reports

cat > /etc/systemd/system/healthcheck-dashboard.service <<SERVICE
[Unit]
Description=Infrastructure Health Check Flask Dashboard
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=vagrant
Group=healthcheck
WorkingDirectory=${PROJECT_DIR}/dashboard
Environment=REPORT_DIR=/var/lib/healthcheck/reports
Environment=FLASK_HOST=0.0.0.0
Environment=FLASK_PORT=5000
ExecStart=/opt/healthcheck/venv/bin/python ${PROJECT_DIR}/dashboard/app.py
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
SERVICE

systemctl daemon-reload
systemctl enable --now healthcheck-dashboard
systemctl restart jenkins

echo "Dashboard: http://192.168.56.10:5000"
