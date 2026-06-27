#!/usr/bin/env bash
# Create the `devin-fix` label and the five remediation issues on the fork.
#
# Requires the GitHub CLI authenticated as the repo owner:
#   gh auth login
# Usage:
#   ./scripts/create_issues.sh            # defaults to sumangit4u/superset
#   REPO=you/superset ./scripts/create_issues.sh
set -euo pipefail

REPO="${REPO:-sumangit4u/superset}"

echo "Ensuring labels exist on $REPO ..."
gh label create devin-fix     --repo "$REPO" --color 5319e7 --description "Auto-remediate with Devin" 2>/dev/null || true
gh label create security      --repo "$REPO" --color d73a4a --description "Security finding"            2>/dev/null || true
gh label create code-quality  --repo "$REPO" --color 0e8a16 --description "Code quality"                2>/dev/null || true

mk () { # title  labels  body
  echo "Creating: $1"
  gh issue create --repo "$REPO" --title "$1" --label "$2" --body "$3"
}

mk "[Security] SQL injection in automation-sandbox/user_lookup.py" "devin-fix,security" \
'`get_user_by_username` and `search_users` build SQL by string-interpolating caller input, allowing SQL injection.

**File:** `automation-sandbox/user_lookup.py`

**Fix:** Use parameterized queries with `?` placeholders and bound parameters. Add a unit test asserting a malicious username (e.g. `'"'"' OR '"'"'1'"'"'='"'"'1`) returns no spurious rows.'

mk "[Security] Weak MD5 hashing and hardcoded secret in token_utils.py" "devin-fix,security" \
'`make_token` uses MD5 (cryptographically broken) and a hardcoded `API_SIGNING_SECRET`.

**File:** `automation-sandbox/token_utils.py`

**Fix:** Use `hmac` with SHA-256 and load the secret from an environment variable. Keep `verify_token` constant-time via `hmac.compare_digest`.'

mk "[Security/Quality] shell=True command injection and bare except in file_processor.py" "devin-fix,security,code-quality" \
'`count_lines` runs `subprocess.check_output(cmd, shell=True)` on interpolated input (command injection). `safe_read` uses a bare `except:`.

**File:** `automation-sandbox/file_processor.py`

**Fix:** Use list-form subprocess arguments without a shell; narrow the exception to `OSError` so `KeyboardInterrupt`/`SystemExit` are not swallowed.'

mk "[Security/Quality] Unsafe yaml.load and mutable default arg in config_loader.py" "devin-fix,security,code-quality" \
'`load_config` calls `yaml.load` without a safe loader (arbitrary object construction) and uses a mutable default argument `defaults=[]`.

**File:** `automation-sandbox/config_loader.py`

**Fix:** Use `yaml.safe_load` and default `defaults=None`, initializing a fresh list inside the function.'

mk "[Security] Missing request timeout and disabled TLS verification in http_client.py" "devin-fix,security" \
'`fetch` and `post_json` issue `requests` calls with no `timeout` (can hang indefinitely); `fetch` sets `verify=False` (disables TLS verification).

**File:** `automation-sandbox/http_client.py`

**Fix:** Add sensible timeouts to both calls and remove `verify=False`.'

echo "Done. View: gh issue list --repo $REPO --label devin-fix"
