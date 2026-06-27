#!/usr/bin/env python3
"""End-to-end simulation — no API key, no network, no server required.

Feeds sample GitHub `issues` webhook payloads through the real orchestrator,
drives the simulated Devin client to completion, prints a summary table, and
writes a static dashboard snapshot to ./data/dashboard.html.

Run:  python -m scripts.simulate   (from the repo root, with SIMULATE=true)
"""
from __future__ import annotations

import os
import sys
import time

os.environ.setdefault("SIMULATE", "true")
os.environ.setdefault("DB_PATH", "data/sim_runs.db")

# allow `python scripts/simulate.py` as well as `-m scripts.simulate`
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.config import CONFIG  # noqa: E402
from app.dashboard import render  # noqa: E402
from app.devin_client import build_client  # noqa: E402
from app.orchestrator import Orchestrator  # noqa: E402
from app.store import Store, to_json  # noqa: E402

SAMPLE_ISSUES = [
    (101, "SQL injection in automation-sandbox/user_lookup.py"),
    (102, "Weak MD5 hashing and hardcoded secret in token_utils.py"),
    (103, "subprocess shell=True command injection in file_processor.py"),
    (104, "Unsafe yaml.load and mutable default arg in config_loader.py"),
    (105, "requests without timeout and verify=False in http_client.py"),
]


def _event(number: int, title: str) -> dict:
    return {
        "action": "labeled",
        "label": {"name": CONFIG.trigger_label},
        "repository": {"full_name": CONFIG.target_repo},
        "issue": {
            "number": number,
            "title": title,
            "body": f"Auto-generated demo issue for {title}.",
            "labels": [{"name": CONFIG.trigger_label}],
        },
    }


def main() -> None:
    # fresh db for a clean demo
    if os.path.exists(CONFIG.db_path):
        os.remove(CONFIG.db_path)

    store = Store(CONFIG.db_path)
    orch = Orchestrator(store, build_client())

    print(f"== Devin remediation simulation ==  mode={'SIMULATE' if CONFIG.effective_simulate else 'LIVE'}\n")

    print("1) Receiving webhook events and starting Devin sessions:")
    for number, title in SAMPLE_ISSUES:
        res = orch.handle_issue_event(_event(number, title))
        print(f"   issue #{number:<4} -> {res.get('session_id', res.get('reason'))}")

    print("\n2) Polling sessions to completion:")
    for tick in range(8):
        updated = orch.poll_active()
        for u in updated:
            print(f"   run {u['run_id']} finished -> {u['result']} {u.get('pr_url') or ''}")
        if not store.active_runs():
            break
        time.sleep(0.2)

    print("\n3) Final metrics:")
    print(to_json(store.metrics()))

    out = "data/dashboard.html"
    with open(out, "w", encoding="utf-8") as f:
        f.write(render(store.metrics(), store.all_runs()))
    print(f"\nDashboard snapshot written to {out}")


if __name__ == "__main__":
    main()
