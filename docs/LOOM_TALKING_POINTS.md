# Loom walkthrough — talking points (≈5 min)

Audience: VP of Engineering + senior ICs evaluating Devin. Keep it crisp; show
the system running, don't just narrate slides.

## 0:00–0:45 · WHAT — the problem
- Every codebase carries a long tail of small, well-scoped issues: security
  findings, dependency bumps, lint/typing debt. They're individually cheap but
  collectively risky, and they never win prioritization against feature work.
- The gap is **finding → fix**. Scanners and trackers tell you a problem exists;
  someone still has to context-switch, write the fix, and open a PR.
- This project closes that gap automatically: **a labeled issue becomes a PR
  waiting for review**, with no human touch until code review.

## 0:45–2:30 · HOW — demo + architecture
- Show the forked Superset repo's `automation-sandbox/` and the five
  `devin-fix` issues (security + code-quality findings).
- Run `python -m scripts.simulate` (or `docker compose up`) live. Narrate:
  1. **Webhook receiver** (`app/webhook.py`) — GitHub `issues` event arrives,
     HMAC-verified, returns `202` immediately.
  2. **Orchestrator** (`app/orchestrator.py`) — builds a *scoped* remediation
     prompt and calls Devin `POST /v1/sessions`. Records the run in SQLite.
     Idempotent on `(repo, issue_number)` so duplicate webhooks are no-ops.
  3. **Background poller** — `GET /v1/session/{id}`, classifies status into
     success/failure, captures the PR URL.
- Open `/dashboard` and `/metrics`. Point to: total runs, active sessions,
  **success rate**, avg resolution time. "This is how an eng leader knows it's
  working." Call out that one run is a **failure** — failures are first-class,
  counted, and visible, not swallowed.
- Key architectural decision to highlight: the **identical interface for real
  and simulated Devin** (`devin_client.py`) — that's what makes the whole thing
  testable and demoable offline, and keeps the orchestrator agnostic.

## 2:30–3:45 · WHY — why Devin specifically
- Each fix isn't templatable: clone the repo, read real code, make a minimal
  change, add a test, open a PR. That's an *autonomous coding agent's* job, not
  a regex codemod or a Dependabot-style version bump.
- Devin runs in its own environment end-to-end, so the orchestrator stays thin:
  it dispatches intent and observes outcomes. We're not building a code-fixer —
  we're building the **control plane** around one.
- The same pipeline generalizes to any issue you can describe in text, across
  any repo — the orchestrator never changes.

## 3:45–5:00 · WHEN — next steps in a real engagement
- **Close the loop on signal source:** wire a scanner (CodeQL/Bandit/Snyk/
  Dependabot) to *auto-file and auto-label* issues, so the trigger is a scan
  result, not a human label.
- **Quality gates:** require Devin's PR to pass CI before requesting review;
  auto-comment results back on the issue; escalate failures to a human queue.
- **Scale & governance:** concurrency limits, per-team routing, cost/usage via
  Devin's org metrics endpoints, and an audit trail (already persisted per run).
- **Feedback to Devin:** feed PR-review comments back into the session via
  `POST /v1/session/{id}/message` for iterative fixes.
- **Observability upgrade:** ship `/metrics` to Prometheus/Grafana for
  throughput, success-rate trends, and MTTR dashboards across the org.

## One-liner to close
"Devin turns the backlog of 'someone should fix that' into a review queue —
and this control plane makes it observable, idempotent, and safe to run on
every finding."
