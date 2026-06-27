"""Unit tests for the orchestration pipeline (run with SIMULATE=true)."""
import os

os.environ["SIMULATE"] = "true"
os.environ["DB_PATH"] = ":memory:"

from app.config import CONFIG  # noqa: E402
from app.devin_client import SimulatedDevinClient, classify_status  # noqa: E402
from app.orchestrator import Orchestrator  # noqa: E402
from app.store import Store  # noqa: E402


def _event(number, label=None, action="labeled"):
    label = label or CONFIG.trigger_label
    return {
        "action": action,
        "label": {"name": label},
        "repository": {"full_name": "sumangit4u/superset"},
        "issue": {
            "number": number,
            "title": f"Issue {number}",
            "body": "body",
            "labels": [{"name": label}],
        },
    }


def _fresh():
    store = Store(":memory:")
    return store, Orchestrator(store, SimulatedDevinClient())


def test_label_triggers_session():
    store, orch = _fresh()
    res = orch.handle_issue_event(_event(1))
    assert res["ok"] is True
    assert res["session_id"].startswith("sim-")
    run = store.get_by_issue("sumangit4u/superset", 1)
    assert run["status"] == "active"


def test_wrong_label_is_skipped():
    store, orch = _fresh()
    res = orch.handle_issue_event(_event(2, label="question"))
    assert res["skipped"] is True


def test_idempotent_no_duplicate_session():
    store, orch = _fresh()
    first = orch.handle_issue_event(_event(3))
    second = orch.handle_issue_event(_event(3))
    assert first["ok"] is True
    assert second["skipped"] is True
    assert second["reason"] == "session already exists"


def test_poll_drives_runs_to_terminal_state():
    store, orch = _fresh()
    for n in range(1, 6):
        orch.handle_issue_event(_event(n))
    for _ in range(10):
        orch.poll_active()
        if not store.active_runs():
            break
    m = store.metrics()
    assert m["total"] == 5
    assert m["active"] == 0
    assert m["success"] + m["failure"] == 5
    assert m["success"] >= 1 and m["failure"] >= 1  # both paths exercised


def test_classify_status_pr_means_success():
    state, result, pr = classify_status(
        {"status_enum": "finished", "pull_request": {"url": "https://x/pull/1"}}
    )
    assert state == "done" and result == "success" and pr.endswith("/pull/1")


def test_classify_status_blocked_is_failure():
    state, result, _ = classify_status({"status_enum": "blocked"})
    assert state == "done" and result == "failure"
