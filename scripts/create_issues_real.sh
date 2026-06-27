#!/usr/bin/env bash
# REAL-CODE track: file a devin-fix issue against actual Apache Superset code
# (not the automation-sandbox demo modules). Devin remediates a genuine,
# low-risk deprecation that exists in the upstream codebase.
#
# Fallback track: scripts/create_issues.sh targets the bounded
# automation-sandbox/ modules — use that if a real-code fix is too broad to
# review on camera or trips Superset's CI.
#
# Requires the GitHub CLI authenticated as the repo owner:
#   gh auth login
# Usage:
#   ./scripts/create_issues_real.sh
#   REPO=you/superset ./scripts/create_issues_real.sh
set -euo pipefail

REPO="${REPO:-sumangit4u/superset}"

echo "Ensuring labels exist on $REPO ..."
gh label create devin-fix    --repo "$REPO" --color 5319e7 --description "Auto-remediate with Devin" 2>/dev/null || true
gh label create code-quality --repo "$REPO" --color 0e8a16 --description "Code quality"              2>/dev/null || true

echo "Creating real-code issue ..."
gh issue create --repo "$REPO" \
  --title "[Code quality] Replace deprecated datetime.utcnow() with timezone-aware datetimes in log-retention code" \
  --label "devin-fix,code-quality" \
  --body 'Python 3.12 deprecates `datetime.utcnow()` (and `datetime.utcfromtimestamp()`): it returns a **naive** datetime with no timezone, which is bug-prone and now emits `DeprecationWarning`. The recommended replacement is `datetime.now(timezone.utc)`.

This issue is scoped to the log-retention code paths to keep the change small and low-risk:

- `superset/commands/logs/prune.py` (1 occurrence)
- `superset/commands/report/log_prune.py` (1 occurrence)
- `superset/daos/log.py` (1 occurrence)

**Fix**
1. Import `timezone` from `datetime` where needed.
2. Replace each `datetime.utcnow()` with `datetime.now(timezone.utc)` in the files above.
3. Keep behavior equivalent (these values are compared against / stored as UTC).
4. Add or update a unit test that asserts the returned datetime is timezone-aware (`tzinfo is not None`).
5. Keep the change limited to the three files listed.

**Context (optional follow-up):** there are ~27 more `datetime.utcnow()` calls across the codebase (notably `superset/commands/report/execute.py` and `superset/utils/cache.py`). Leave those for a separate PR so this one stays reviewable.'

echo "Done. View: gh issue list --repo $REPO --label devin-fix"
