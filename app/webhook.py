"""FastAPI app: GitHub webhook receiver + observability endpoints.

Endpoints
---------
POST /webhook    GitHub `issues` events (HMAC-verified). Triggers Devin.
GET  /healthz    liveness probe
GET  /runs       JSON list of all runs
GET  /metrics    Prometheus-style text metrics (and JSON at /metrics.json)
GET  /dashboard  human-friendly HTML dashboard
"""
from __future__ import annotations

import asyncio
import hashlib
import hmac
import logging

from fastapi import FastAPI, Header, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse, PlainTextResponse, RedirectResponse

from .config import CONFIG
from .dashboard import render
from .devin_client import build_client
from .orchestrator import Orchestrator
from .store import Store

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
log = logging.getLogger("webhook")

app = FastAPI(title="Devin-Superset Remediation Automation", version="1.0.0")
store = Store(CONFIG.db_path)
orchestrator = Orchestrator(store, build_client())


@app.on_event("startup")
async def _start_poller() -> None:
    async def loop() -> None:
        while True:
            await asyncio.sleep(CONFIG.poll_interval_seconds)
            try:
                await asyncio.to_thread(orchestrator.poll_active)
            except Exception:  # noqa: BLE001
                log.exception("poller iteration failed")

    asyncio.create_task(loop())
    mode = "SIMULATE" if CONFIG.effective_simulate else "LIVE"
    log.info("Started. Mode=%s  trigger-label=%s  repo=%s", mode, CONFIG.trigger_label, CONFIG.target_repo)


def _verify_signature(body: bytes, signature: str | None) -> None:
    """Validate GitHub's X-Hub-Signature-256 header when a secret is configured."""
    if not CONFIG.webhook_secret:
        return  # unsigned mode (local/demo)
    if not signature or not signature.startswith("sha256="):
        raise HTTPException(status_code=401, detail="missing signature")
    digest = hmac.new(CONFIG.webhook_secret.encode(), body, hashlib.sha256).hexdigest()
    if not hmac.compare_digest(f"sha256={digest}", signature):
        raise HTTPException(status_code=401, detail="bad signature")


@app.post("/webhook")
async def webhook(
    request: Request,
    x_github_event: str = Header(default=""),
    x_hub_signature_256: str | None = Header(default=None),
) -> JSONResponse:
    body = await request.body()
    _verify_signature(body, x_hub_signature_256)
    payload = await request.json()

    if x_github_event == "ping":
        return JSONResponse({"ok": True, "pong": True})
    if x_github_event != "issues":
        return JSONResponse({"skipped": True, "reason": f"event '{x_github_event}' ignored"})

    result = await asyncio.to_thread(orchestrator.handle_issue_event, payload)
    return JSONResponse(result, status_code=202 if result.get("ok") else 200)


@app.get("/healthz")
async def healthz() -> dict:
    return {"status": "ok", "mode": "simulate" if CONFIG.effective_simulate else "live"}


@app.get("/runs")
async def runs() -> JSONResponse:
    return JSONResponse(store.all_runs())


@app.get("/metrics.json")
async def metrics_json() -> JSONResponse:
    return JSONResponse(store.metrics())


@app.get("/metrics")
async def metrics() -> PlainTextResponse:
    m = store.metrics()
    lines = [
        "# HELP devin_runs_total Total remediation runs recorded",
        "# TYPE devin_runs_total counter",
        f"devin_runs_total {m['total']}",
        "# HELP devin_runs_active Sessions currently in progress",
        "# TYPE devin_runs_active gauge",
        f"devin_runs_active {m['active']}",
        "# HELP devin_runs_success Runs that produced a PR",
        "# TYPE devin_runs_success counter",
        f"devin_runs_success {m['success']}",
        "# HELP devin_runs_failure Runs that ended without success",
        "# TYPE devin_runs_failure counter",
        f"devin_runs_failure {m['failure']}",
        "# HELP devin_success_rate Success / completed ratio",
        "# TYPE devin_success_rate gauge",
        f"devin_success_rate {m['success_rate'] if m['success_rate'] is not None else 0}",
        "# HELP devin_avg_resolution_seconds Mean time from trigger to terminal state",
        "# TYPE devin_avg_resolution_seconds gauge",
        f"devin_avg_resolution_seconds {m['avg_resolution_seconds']}",
    ]
    return PlainTextResponse("\n".join(lines) + "\n")


@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard() -> HTMLResponse:
    return HTMLResponse(render(store.metrics(), store.all_runs()))


@app.get("/")
async def root() -> RedirectResponse:
    return RedirectResponse(url="/dashboard")
