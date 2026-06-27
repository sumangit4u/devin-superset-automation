"""Thin client for the Devin REST API (v1) plus an in-process simulator.

The real client and the simulator share the same interface so the rest of the
system never needs to know which one is in use:

    create_session(prompt, tags) -> {"session_id", "url"}
    get_session(session_id)      -> {"status_enum", "pull_request", ...}

Docs: https://docs.devin.ai/api-reference/v1/overview
"""
from __future__ import annotations

import itertools
import time
from typing import Any, Protocol

import httpx

from .config import CONFIG


class DevinClient(Protocol):
    def create_session(self, prompt: str, tags: list[str] | None = None) -> dict[str, Any]: ...
    def get_session(self, session_id: str) -> dict[str, Any]: ...


class RealDevinClient:
    """Talks to the live Devin API using a Bearer token."""

    def __init__(self, api_key: str, base_url: str) -> None:
        self._base = base_url.rstrip("/")
        self._headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }

    def create_session(self, prompt: str, tags: list[str] | None = None) -> dict[str, Any]:
        # POST /v1/sessions  -> { session_id, url, is_new_session }
        payload: dict[str, Any] = {"prompt": prompt, "idempotent": True}
        if tags:
            payload["tags"] = tags
        with httpx.Client(timeout=30) as client:
            resp = client.post(f"{self._base}/sessions", json=payload, headers=self._headers)
            resp.raise_for_status()
            return resp.json()

    def get_session(self, session_id: str) -> dict[str, Any]:
        # GET /v1/session/{session_id} -> { status_enum, structured_output, ... }
        with httpx.Client(timeout=30) as client:
            resp = client.get(f"{self._base}/session/{session_id}", headers=self._headers)
            resp.raise_for_status()
            return resp.json()


class SimulatedDevinClient:
    """Deterministic, offline stand-in for the Devin API.

    A session advances RUNNING -> WORKING -> finished over a few polls and then
    reports a fake pull request, so the full pipeline (and the dashboard) can be
    demonstrated without network access or a key.
    """

    # status timeline returned on successive get_session() calls
    _TIMELINE = ["RUNNING", "RUNNING", "working", "working", "finished"]

    def __init__(self) -> None:
        self._counter = itertools.count(1)
        self._created_at: dict[str, float] = {}
        self._polls: dict[str, int] = {}
        self._fail: dict[str, bool] = {}

    def create_session(self, prompt: str, tags: list[str] | None = None) -> dict[str, Any]:
        n = next(self._counter)
        sid = f"sim-{n:04d}"
        self._created_at[sid] = time.time()
        self._polls[sid] = 0
        # deterministically fail ~1 in 4 to exercise failure paths in the demo
        self._fail[sid] = (n % 4 == 0)
        return {
            "session_id": sid,
            "url": f"https://app.devin.ai/sessions/{sid}",
            "is_new_session": True,
        }

    def get_session(self, session_id: str) -> dict[str, Any]:
        self._polls[session_id] = self._polls.get(session_id, 0) + 1
        idx = min(self._polls[session_id] - 1, len(self._TIMELINE) - 1)
        status = self._TIMELINE[idx]
        out: dict[str, Any] = {"session_id": session_id, "status_enum": status}
        if status == "finished":
            if self._fail.get(session_id):
                out["status_enum"] = "blocked"
                out["structured_output"] = {"error": "Could not satisfy all checks"}
            else:
                num = session_id.split("-")[-1]
                out["pull_request"] = {
                    "url": f"https://github.com/{CONFIG.target_repo}/pull/{int(num)}"
                }
                out["structured_output"] = {"pr_url": out["pull_request"]["url"]}
        return out


def build_client() -> DevinClient:
    if CONFIG.effective_simulate:
        return SimulatedDevinClient()
    return RealDevinClient(CONFIG.devin_api_key, CONFIG.devin_api_base)


# --- helpers for interpreting Devin status -------------------------------------------------

_TERMINAL_OK = {"finished", "completed", "succeeded", "done"}
_TERMINAL_FAIL = {"blocked", "stopped", "failed", "expired", "cancelled", "canceled"}


def classify_status(session: dict[str, Any]) -> tuple[str, str | None, str | None]:
    """Map a Devin session payload to (state, result, pr_url).

    state  : "active" | "done"
    result : None | "success" | "failure"
    pr_url : extracted pull-request URL if present
    """
    status = str(session.get("status_enum") or session.get("status") or "").lower()
    pr_url = _extract_pr_url(session)

    if status in _TERMINAL_OK or pr_url:
        return "done", "success", pr_url
    if status in _TERMINAL_FAIL:
        return "done", "failure", pr_url
    return "active", None, pr_url


def _extract_pr_url(session: dict[str, Any]) -> str | None:
    pr = session.get("pull_request")
    if isinstance(pr, dict) and pr.get("url"):
        return pr["url"]
    so = session.get("structured_output")
    if isinstance(so, dict):
        for key in ("pr_url", "pull_request_url", "pr"):
            val = so.get(key)
            if isinstance(val, str) and val.startswith("http"):
                return val
    return None
