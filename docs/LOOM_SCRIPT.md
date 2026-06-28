# Loom video — full script (≈5 minutes)

Audience: VP of Engineering + senior ICs, curious about Devin.
Format: `[SHOW]` = what's on screen · `[SAY]` = read this aloud.
Pace ~140 wpm. Practice the demo once so the PR is ready to reveal.

---

## 0:00 – 0:55 · WHAT (the problem)

`[SHOW]` Your face / title slide: "Autonomous issue remediation with Devin".

`[SAY]`
"Hi — I'm going to show you a system that takes a labeled GitHub issue and turns
it into a reviewed pull request, with no human writing the code.

Every engineering org has the same backlog problem. There's a long tail of
small, well-scoped work — security findings, dependency bumps, lint and typing
debt. Each item is cheap on its own, but collectively it's real risk, and it
never wins prioritization against feature work. So it sits.

The gap I'm closing is the one between *'a problem has been identified'* and
*'a fix is waiting for review.'* Today a human has to context-switch into that
issue, understand the code, write the fix, and open a PR. My system makes that
happen automatically the moment someone says 'yes, fix this' — by adding a
label."

---

## 0:55 – 3:00 · HOW (demo + architecture)

`[SHOW]` The fork on GitHub → open `automation-sandbox/user_lookup.py`.

`[SAY]`
"Here's a real, broken file in my Superset fork. This function builds a SQL
query by gluing user input straight into the string — a classic SQL injection.
There's a GitHub issue describing exactly that, labeled `devin-fix`."

`[SHOW]` The issue on GitHub with the `devin-fix` label.

`[SAY]`
"That label is the trigger. Let me show the system reacting to it live."

`[SHOW]` Terminal 1: `docker compose up` already running. Browser on
`http://localhost:8000/dashboard` (empty).

`[SAY]`
"This is my orchestrator running in Docker, and its live dashboard. Right now
it's empty. I'll fire the same event GitHub sends when you apply the label."

`[SHOW]` Terminal 2: run
`python scripts/trigger.py 1 "SQL injection in automation-sandbox/user_lookup.py"`

`[SAY]`
"Behind that one command, four things just happened. Let me walk the
architecture while it works."

`[SHOW]` Briefly show `app/webhook.py`, then `app/orchestrator.py`.

`[SAY]`
"One — a FastAPI webhook receiver takes the GitHub event, verifies its
signature, and returns immediately. Two — the orchestrator builds a tightly
scoped prompt from the issue and calls Devin's API to start a session. Three —
it records the run in SQLite, and it's idempotent: the same issue can never spin
up two Devin sessions, which matters when GitHub retries webhooks. Four — a
background poller watches the session until it finishes.

The decision I'm proudest of: the orchestrator talks to an *interface*, not to
Devin directly. There's a real Devin client and a simulated one behind the same
methods — so the whole system is testable and demoable offline, and the core
logic never changes."

`[SHOW]` Dashboard now showing the run as `active`; click the Devin **session**
link to show Devin working in its own environment.

`[SAY]`
"And here's the part that matters — this is Devin, in its own cloud environment,
having cloned the repo, found the file, and writing the fix. I'm not scripting
the edit. I'm handing it intent and watching it work."

`[SHOW]` Back to dashboard → row flips to `done / success` → click the **PR**.

`[SAY]`
"Done. It opened a pull request. The injectable query is now parameterized with
bound arguments — and notice it added a test. That's a reviewable PR, produced
end to end with zero human coding."

`[SHOW]` `http://localhost:8000/metrics` or the dashboard cards.

`[SAY]`
"For the leaders in the room: this is how you'd know it's working. Total runs,
active sessions, success rate, average time-to-resolution — and failures are
first-class. When Devin can't satisfy the checks, that's recorded as a failure
and shown here, not swallowed. These metrics are Prometheus-scrapable, so they
drop straight into Grafana."

---

## 3:00 – 4:00 · WHY (why Devin specifically)

`[SHOW]` Split: the broken file vs. the PR diff.

`[SAY]`
"Why does this need Devin, and not a script? Because none of these fixes are
templatable. Each one requires cloning the repo, reading real code in context,
making a minimal correct change, adding a test, and opening a PR. That's
judgment, not a regex. A codemod can bump a version string; it can't reason
about whether a query is exploitable and rewrite it safely.

What that buys me architecturally is leverage. Because Devin handles the hard
part autonomously, my orchestrator stays thin — maybe a few hundred lines. I'm
not building a code-fixer; I'm building the *control plane* around an autonomous
one. And the same pipeline generalizes to any issue you can describe in
English, across any repository, without changing a line of the orchestrator.
That's the unlock you don't get without an autonomous agent."

---

## 4:00 – 5:00 · WHEN (next steps)

`[SHOW]` The README architecture diagram, or a simple roadmap slide.

`[SAY]`
"In a real customer engagement, here's how I'd extend it.

First, close the loop on the trigger: wire a scanner — CodeQL, Bandit, Snyk,
Dependabot — to auto-file and auto-label issues, so the input is a scan result,
not a human label.

Second, add quality gates: require Devin's PR to pass CI before it requests
review, comment the results back on the issue, and route anything that fails to
a human queue.

Third, governance at scale: concurrency limits, per-team routing, and cost and
usage tracking through Devin's org metrics endpoints — with the per-run audit
trail I already persist.

And fourth, make it iterative: feed pull-request review comments back into the
Devin session so it revises its own work.

The one-liner I'd leave you with: Devin turns 'someone should fix that' into a
review queue — and this control plane makes it observable, idempotent, and safe
to run on every finding. Thanks for watching."

---

### Pre-record checklist
- `docker compose up --build` running; `.env` has a real `DEVIN_API_KEY`, `SIMULATE=false`.
- Devin has GitHub access to `sumangit4u/superset`.
- Dashboard open at `http://localhost:8000/dashboard`.
- The target issue exists and the broken file is open in a tab.
- Do a dry run so you know roughly how long Devin takes; if it's slow, start the
  trigger before narrating the architecture so the PR is ready by 3:00.
