"""Core orchestration: turn a GitHub issue event into a managed Devin session."""
from __future__ import annotations

import logging
from typing import Any

from .config import CONFIG
from .devin_client import DevinClient, classify_status
from .store import Store

log = logging.getLogger("orchestrator")


PROMPT_TEMPLATE = """You are remediating a tracked issue in the repository {repo}.

Issue #{number}: {title}

{body}

Instructions:
1. Check out the repository {repo} (default branch).
2. Implement a minimal, focused fix for ONLY the problem described above.
3. Add or update a unit test that proves the fix when practical.
4. Open a pull request that closes #{number}. Reference the issue in the PR body.
5. Keep the change scoped to the file(s) named in the issue.
"""


class Orchestrator:
    def __init__(self, store: Store, client: DevinClient) -> None:
        self._store = store
        self._client = client

    # -- event entry point -------------------------------------------------------------
    def handle_issue_event(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Process a GitHub `issues` webhook payload. Returns a small status dict."""
        action = payload.get("action")
        issue = payload.get("issue") or {}
        repo = (payload.get("repository") or {}).get("full_name") or CONFIG.target_repo
        number = issue.get("number")
        title = issue.get("title", "")

        if number is None:
            return {"skipped": True, "reason": "no issue number"}

        if not self._should_trigger(payload):
            return {"skipped": True, "reason": f"action '{action}' / label not '{CONFIG.trigger_label}'"}

        # idempotency: never start a second session for the same issue
        existing = self._store.get_by_issue(repo, number)
        if existing and existing.get("session_id"):
            return {
                "skipped": True,
                "reason": "session already exists",
                "run_id": existing["id"],
                "session_url": existing.get("session_url"),
            }

        run_id = self._store.create_run(repo, number, title)
        prompt = PROMPT_TEMPLATE.format(
            repo=repo, number=number, title=title, body=issue.get("body") or "(no description)"
        )

        try:
            session = self._client.create_session(prompt, tags=["devin-fix", repo])
        except Exception as exc:  # noqa: BLE001 - record and surface, don't crash the webhook
            log.exception("Failed to create Devin session for issue #%s", number)
            self._store.update_run(run_id, status="error", error=str(exc))
            return {"ok": False, "run_id": run_id, "error": str(exc)}

        self._store.update_run(
            run_id,
            session_id=session.get("session_id"),
            session_url=session.get("url"),
            status="active",
        )
        log.info("Started Devin session %s for issue #%s", session.get("session_id"), number)
        return {
            "ok": True,
            "run_id": run_id,
            "session_id": session.get("session_id"),
            "session_url": session.get("url"),
        }

    def _should_trigger(self, payload: dict[str, Any]) -> bool:
        action = payload.get("action")
        issue = payload.get("issue") or {}
        label_names = {l.get("name") for l in issue.get("labels", []) if isinstance(l, dict)}

        if action == "labeled":
            # the specific label just added
            return (payload.get("label") or {}).get("name") == CONFIG.trigger_label
        if action in {"opened", "reopened"}:
            return CONFIG.trigger_label in label_names
        return False

    # -- polling -----------------------------------------------------------------------
    def poll_active(self) -> list[dict[str, Any]]:
        """Refresh every active run from Devin and persist terminal results."""
        updated: list[dict[str, Any]] = []
        for run in self._store.active_runs():
            try:
                session = self._client.get_session(run["session_id"])
            except Exception as exc:  # noqa: BLE001
                log.warning("poll failed for %s: %s", run["session_id"], exc)
                continue
            state, result, pr_url = classify_status(session)
            if state == "done":
                self._store.update_run(
                    run["id"], status="done", result=result, pr_url=pr_url
                )
                log.info(
                    "Run %s (issue #%s) -> %s%s",
                    run["id"], run["issue_number"], result, f" {pr_url}" if pr_url else "",
                )
                updated.append({"run_id": run["id"], "result": result, "pr_url": pr_url})
            elif pr_url and not run.get("pr_url"):
                self._store.update_run(run["id"], pr_url=pr_url)
        return updated
