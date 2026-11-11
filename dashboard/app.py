from __future__ import annotations

import json
import os
import re
from pathlib import Path
from typing import Any

from flask import Flask, abort, jsonify, render_template

app = Flask(__name__, template_folder="templates")
REPORT_ROOT = Path(os.environ.get("REPORT_DIR", "/var/lib/healthcheck/reports"))
RUN_ID_PATTERN = re.compile(r"^[A-Za-z0-9_-]+$")


def load_runs() -> list[dict[str, Any]]:
    """Load report folders newest first; each folder represents one Jenkins run."""
    if not REPORT_ROOT.exists():
        return []

    runs: list[dict[str, Any]] = []
    for run_dir in sorted(
        (p for p in REPORT_ROOT.iterdir() if p.is_dir()),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    ):
        hosts = []
        for report_file in sorted(run_dir.glob("*.json")):
            try:
                data = json.loads(report_file.read_text(encoding="utf-8"))
                data["report_file"] = report_file.name
                hosts.append(data)
            except (OSError, json.JSONDecodeError):
                app.logger.exception("Unable to read report %s", report_file)
        if hosts:
            runs.append({"run_id": run_dir.name, "hosts": hosts})
    return runs


@app.get("/")
def index():
    return render_template("index.html")


@app.get("/api/summary")
def api_summary():
    runs = load_runs()
    latest = runs[0] if runs else {"run_id": None, "hosts": []}
    hosts = latest["hosts"]
    return jsonify(
        {
            "latest_run": latest["run_id"],
            "host_count": len(hosts),
            "ok_count": sum(1 for h in hosts if h.get("status") == "OK"),
            "warning_count": sum(1 for h in hosts if h.get("status") == "WARNING"),
            "critical_count": sum(1 for h in hosts if h.get("status") == "CRITICAL"),
            "hosts": hosts,
            "history": [
                {"run_id": run["run_id"], "host_count": len(run["hosts"])}
                for run in runs[:20]
            ],
        }
    )


@app.get("/api/run/<run_id>")
def api_run(run_id: str):
    if not RUN_ID_PATTERN.fullmatch(run_id):
        abort(404)
    for run in load_runs():
        if run["run_id"] == run_id:
            return jsonify(run)
    abort(404)


if __name__ == "__main__":
    host = os.environ.get("FLASK_HOST", "0.0.0.0")
    port = int(os.environ.get("FLASK_PORT", "5000"))
    app.run(host=host, port=port, debug=False)
