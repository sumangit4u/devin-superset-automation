#!/usr/bin/env python3
"""Send a sample GitHub `issues` webhook to a running server.

Useful for demoing the live HTTP path without configuring a real GitHub webhook.

Run (server must be up):  python scripts/trigger.py 999 "Fix the thing"
"""
from __future__ import annotations

import hashlib
import hmac
import json
import os
import sys
import urllib.request

URL = os.getenv("WEBHOOK_URL", "http://localhost:8000/webhook")
SECRET = os.getenv("GITHUB_WEBHOOK_SECRET", "")
LABEL = os.getenv("TRIGGER_LABEL", "devin-fix")
REPO = os.getenv("TARGET_REPO", "sumangit4u/superset")


def main() -> None:
    number = int(sys.argv[1]) if len(sys.argv) > 1 else 9001
    title = sys.argv[2] if len(sys.argv) > 2 else "Demo: SQL injection in user_lookup.py"
    payload = {
        "action": "labeled",
        "label": {"name": LABEL},
        "repository": {"full_name": REPO},
        "issue": {
            "number": number,
            "title": title,
            "body": "Triggered via scripts/trigger.py",
            "labels": [{"name": LABEL}],
        },
    }
    body = json.dumps(payload).encode()
    headers = {"Content-Type": "application/json", "X-GitHub-Event": "issues"}
    if SECRET:
        sig = hmac.new(SECRET.encode(), body, hashlib.sha256).hexdigest()
        headers["X-Hub-Signature-256"] = f"sha256={sig}"

    req = urllib.request.Request(URL, data=body, headers=headers, method="POST")
    with urllib.request.urlopen(req) as resp:  # noqa: S310 - local trusted URL
        print(resp.status, resp.read().decode())


if __name__ == "__main__":
    main()
