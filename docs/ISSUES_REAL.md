# Real-code track (Part 1, authentic variant)

Two ways to give Devin something to remediate. Pick per demo:

| Track | Targets | Script | When to use |
|-------|---------|--------|-------------|
| **Sandbox** (default / fallback) | `automation-sandbox/` planted modules | `scripts/create_issues.sh` | Safe, bounded, visually clear PRs. Can't break Superset CI. Best for a reliable on-camera demo. |
| **Real code** (authentic) | Actual upstream Superset files | `scripts/create_issues_real.sh` | Proves Devin fixes a genuine issue in the real codebase. Slightly higher risk (touches production code + CI). |

## The real finding

`datetime.utcnow()` is **deprecated in Python 3.12+**. It returns a *naive*
datetime (no timezone), which is error-prone; the documented replacement is
`datetime.now(timezone.utc)`. It appears **27 times** across real Superset files:

```
21  superset/commands/report/execute.py
 2  superset/utils/cache.py
 1  superset/utils/dates.py
 1  superset/daos/log.py
 1  superset/commands/report/log_prune.py
 1  superset/commands/logs/prune.py
```

The filed issue is deliberately **scoped to the three log-retention files**
(`commands/logs/prune.py`, `commands/report/log_prune.py`, `daos/log.py`) so
Devin's PR is small and reviewable. The larger sweep is noted as optional
follow-up.

## How it runs (same pipeline, real target)

1. `./scripts/create_issues_real.sh` files the issue with the `devin-fix` label.
2. The label triggers the orchestrator (webhook, or `scripts/trigger.py` locally).
3. Devin clones the repo, replaces the deprecated calls, adds a timezone-aware
   test, and opens a PR — observable on `/dashboard`.

## Fallback

If the real-code PR is too broad to review on camera, or Superset's CI is noisy,
run `scripts/create_issues.sh` instead and demo the sandbox fix
(`automation-sandbox/user_lookup.py` SQL-injection → parameterized query). The
orchestrator code is identical; only the target differs.
