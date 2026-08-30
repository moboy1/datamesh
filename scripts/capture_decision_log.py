#!/usr/bin/env python3
"""
OPA Decision Log Capture
Queries the OPA decisions endpoint and saves structured audit evidence to logs/.
Run after executing the Pytest compliance scenario tests.

Usage:
    python scripts/capture_decision_log.py
"""

import os
import json
import datetime
import requests

OPA_URL  = os.getenv("OPA_URL", "http://localhost:8181")
LOG_DIR  = os.path.join(os.path.dirname(__file__), "..", "logs")


def capture():
    os.makedirs(LOG_DIR, exist_ok=True)

    # OPA exposes its in-memory decision log via /v1/data (with console logger)
    # For persistent logs, we query the full data store state as a snapshot
    resp = requests.get(f"{OPA_URL}/v1/data", timeout=5)
    resp.raise_for_status()

    timestamp = datetime.datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
    filename  = os.path.join(LOG_DIR, f"opa_snapshot_{timestamp}.json")

    with open(filename, "w") as f:
        json.dump(resp.json(), f, indent=2)

    print(f"OPA data snapshot saved: {filename}")

    # Also query each policy endpoint directly and log the structure
    policies = {
        "rbac":        "datamesh/query",
        "masking":     "datamesh/masking",
        "crossdomain": "datamesh/crossdomain",
    }

    summary = {}
    for name, path in policies.items():
        r = requests.get(f"{OPA_URL}/v1/data/{path}", timeout=5)
        if r.status_code == 200:
            summary[name] = r.json().get("result", {})

    summary_file = os.path.join(LOG_DIR, f"policy_summary_{timestamp}.json")
    with open(summary_file, "w") as f:
        json.dump(summary, f, indent=2)

    print(f"Policy summary saved:    {summary_file}")


if __name__ == "__main__":
    capture()
