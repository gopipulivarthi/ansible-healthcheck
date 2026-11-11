#!/usr/bin/env python3
"""Email a Jenkins health-check run using Gmail SMTP with an App Password."""
from __future__ import annotations

import argparse
import json
import os
import smtplib
import ssl
from email.message import EmailMessage
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--report-dir", required=True, help="Root directory containing run folders")
    parser.add_argument("--run-id", required=True, help="Run folder to email, e.g. build-12")
    args = parser.parse_args()

    sender = os.environ.get("GMAIL_USER")
    recipient = os.environ.get("REPORT_EMAIL_TO")
    app_password = os.environ.get("GMAIL_APP_PASSWORD")
    if app_password:
        app_password = app_password.replace(" ", "")
    if not sender or not recipient or not app_password:
        raise SystemExit("Set GMAIL_USER, REPORT_EMAIL_TO and GMAIL_APP_PASSWORD environment variables.")

    run_dir = Path(args.report_dir) / args.run_id
    report_files = sorted(run_dir.glob("*.json"))
    if not report_files:
        raise SystemExit(f"No JSON reports found in {run_dir}")

    reports = [json.loads(path.read_text(encoding="utf-8")) for path in report_files]
    counts = {status: sum(1 for item in reports if item.get("status") == status) for status in ("OK", "WARNING", "CRITICAL")}
    overall = "CRITICAL" if counts["CRITICAL"] else "WARNING" if counts["WARNING"] else "OK"

    rows = []
    for report in reports:
        disk = report.get("disk_used_pct", report.get("disk_c_used_pct", report.get("disk_root_used_pct", "—")))
        cpu = report.get("cpu_load_pct", f"Load {report.get('cpu_load_1m', '—')}")
        rows.append(
            "<tr>"
            f"<td>{report.get('hostname', '—')}</td>"
            f"<td>{report.get('platform', '—')}</td>"
            f"<td>{cpu}</td>"
            f"<td>{report.get('memory_used_pct', '—')}%</td>"
            f"<td>{disk}%</td>"
            f"<td><b>{report.get('status', 'UNKNOWN')}</b></td>"
            "</tr>"
        )

    message = EmailMessage()
    message["From"] = sender
    message["To"] = recipient
    message["Subject"] = f"[Health Check] {args.run_id}: {overall}"
    message.set_content(
        f"Health-check run {args.run_id}\nServers: {len(reports)} | OK: {counts['OK']} | "
        f"Warning: {counts['WARNING']} | Critical: {counts['CRITICAL']}\n"
        "See the attached JSON reports for details."
    )
    html = f"""<html><body style='font-family:Arial,sans-serif'>
    <h2>Infrastructure Health Check: {overall}</h2>
    <p>Run: <b>{args.run_id}</b> | Servers: {len(reports)} | Healthy: {counts['OK']} |
    Warning: {counts['WARNING']} | Critical: {counts['CRITICAL']}</p>
    <table cellpadding='8' cellspacing='0' border='1' style='border-collapse:collapse'>
    <tr><th>Host</th><th>Platform</th><th>CPU</th><th>Memory</th><th>Disk</th><th>Status</th></tr>
    {''.join(rows)}</table><p>Detailed JSON files are attached.</p></body></html>"""
    message.add_alternative(html, subtype="html")

    for path in report_files:
        message.add_attachment(
            path.read_bytes(),
            maintype="application",
            subtype="json",
            filename=path.name,
        )

    context = ssl.create_default_context()
    with smtplib.SMTP_SSL("smtp.gmail.com", 465, context=context, timeout=30) as smtp:
        smtp.login(sender, app_password)
        smtp.send_message(message)
    print(f"Report email sent to {recipient} for {args.run_id}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
