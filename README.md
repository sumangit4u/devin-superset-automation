# Devin × Superset — Event-Driven Remediation Automation

An autonomous pipeline that watches a GitHub repository for issues labeled
**`devin-fix`**, spins up a [Devin](https://docs.devin.ai) session to fix each
one, manages that session to completion, and surfaces the result as a pull
request — with a live observability dashboard so an engineering leader can see,
at a glance, that it is working.

```
GitHub issue labeled `devin-fix`
        │  (webhook: X-GitHub-Event: issues)
        ▼
┌─────────────────────────────────────────────┐
│  FastAPI webhook receiver  (app/webhook.py)  │
│   • HMAC-verifies the GitHub signature       │
│   • dispatches to the Orchestrator           │
└───────────────┬─────────────────────────────┘
                ▼
┌─────────────────────────────────────────────┐
│  Orchestrator  (app/orchestrator.py)         │
│   • builds a scoped remediation prompt       │
│   • POST /v1/sessions  → Devin               │
│   • records the run in SQLite (idempotent)   │
└───────────────┬─────────────────────────────┘
                ▼
┌─────────────────────────────────────────────┐
│  Background poller (every POLL_INTERVAL s)   │
│   • GET /v1/session/{id} for active runs     │
│   • classifies status → success / failure    │
│   • captures the PR URL                       │
└───────────────┬─────────────────────────────┘
                ▼
   Observability:  /dashboard · /metrics · /runs
```

## Why this matters

Backlogs of small, well-scoped issues — security findings, dependency bumps,
lint debt — rarely get prioritized, yet they accumulate risk. This system turns
**"a finding exists"** into **"a PR is waiting for review"** with no human in the
loop until code review. Devin is uniquely suited because each fix needs an agent
that can clone the repo, reason about real code, edit it, run tests, and open a
PR — not a templated script.

## Quick start

### Option A — Simulation (no API key, no network)

Proves the entire pipeline end-to-end against an in-process fake Devin.

```bash
pip install -r requirements.txt
python -m scripts.simulate
```

You'll see five sample issues flow through to sessions, get polled to terminal
state (the simulator deterministically fails ~1 in 4 to exercise the failure
path), final metrics print, and a dashboard snapshot is written to
`data/dashboard.html`.

### Option B — Run the live service with Docker

```bash
cp .env.example .env        # then fill in DEVIN_API_KEY, GITHUB_WEBHOOK_SECRET
docker compose up --build
```

- Dashboard:  http://localhost:8000/dashboard
- Metrics:    http://localhost:8000/metrics  (Prometheus text) · `/metrics.json`
- Health:     http://localhost:8000/healthz

With `DEVIN_API_KEY` empty the service automatically runs in **simulate** mode,
so `docker compose up` always gives you a working demo.

### Trigger it

Point a GitHub webhook (`Settings → Webhooks`, content-type `application/json`,
event = *Issues*, secret = `GITHUB_WEBHOOK_SECRET`) at
`https://<your-host>/webhook`. Then label any issue `devin-fix`.

Or, without configuring GitHub, replay a sample event against a running server:

```bash
python scripts/trigger.py 123 "SQL injection in user_lookup.py"
```

## Configuration

All via environment (`.env.example` documents every key):

| Variable | Default | Purpose |
|----------|---------|---------|
| `DEVIN_API_KEY` | — | Devin API key. Empty ⇒ simulate mode. |
| `DEVIN_API_BASE` | `https://api.devin.ai/v1` | Devin API base URL. |
| `GITHUB_WEBHOOK_SECRET` | — | Enables HMAC verification of webhooks. |
| `TARGET_REPO` | `sumangit4u/superset` | Repo issues belong to. |
| `TRIGGER_LABEL` | `devin-fix` | Label that triggers remediation. |
| `SIMULATE` | `false` | Force simulation even with a key. |
| `POLL_INTERVAL_SECONDS` | `15` | Session poll cadence. |

## Observability — "how would I know this is working?"

| Surface | Answers |
|---------|---------|
| `/dashboard` | Live table of every run: issue → status → result → Devin session → PR, plus headline cards (total, active, success rate, avg resolution time). Auto-refreshes. |
| `/metrics` | Prometheus-scrapable counters/gauges: `devin_runs_total`, `devin_runs_active`, `devin_runs_success`, `devin_runs_failure`, `devin_success_rate`, `devin_avg_resolution_seconds`. |
| `/runs` | Raw JSON of every run for ad-hoc analysis. |
| Structured logs | Each lifecycle transition (session started, run resolved) is logged. |

Every run is persisted to SQLite (`runs` table), so metrics survive restarts and
can be exported to any BI/monitoring tool.

## Design decisions

- **Webhook-triggered, not polling GitHub.** Reacts in real time to the
  `labeled` event; the label is the human's intentional "yes, fix this" signal.
- **Idempotent by `(repo, issue_number)`.** A duplicate webhook never starts a
  second Devin session — enforced by a unique constraint and a pre-flight check.
- **Same interface for real and simulated Devin** (`devin_client.py`), so the
  full system is testable and demoable with zero external dependencies.
- **Failures are first-class.** A blocked/stopped session is recorded as a
  `failure`, counted in metrics, and shown on the dashboard — not swallowed.
- **Decoupled poller.** Session management is asynchronous; the webhook returns
  immediately (202) while a background task drives sessions to completion.

## Tests

```bash
pip install pytest
python -m pytest -q
```

Covers triggering, label filtering, idempotency, the poll→terminal transition,
and status classification.

## Repository layout

```
app/
  config.py         env-driven configuration
  devin_client.py   real + simulated Devin API clients, status classification
  store.py          SQLite persistence + metrics aggregation
  orchestrator.py   event → session → record; poll → resolve
  dashboard.py      dependency-free HTML dashboard
  webhook.py        FastAPI app (webhook + observability endpoints)
scripts/
  simulate.py       keyless end-to-end demo
  trigger.py        replay a sample webhook at a running server
tests/
  test_pipeline.py  unit tests (run with SIMULATE=true)
Dockerfile · docker-compose.yml · .env.example
```

The companion targets live in the forked Superset repo under
[`automation-sandbox/`](https://github.com/sumangit4u/superset/tree/master/automation-sandbox):
intentionally-flawed sample modules, one per `devin-fix` issue.
