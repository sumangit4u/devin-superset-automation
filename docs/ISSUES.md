# Selected issues (Part 1)

Five issues filed against the forked Superset repo, each targeting a
self-contained module in `automation-sandbox/`. All carry the `devin-fix` label
that triggers the automation. Two classes: **security** and **code quality**.

| # | Title | Class | File | Fix |
|---|-------|-------|------|-----|
| 1 | SQL injection via string-formatted queries | Security | `automation-sandbox/user_lookup.py` | Use parameterized queries (`?` placeholders) |
| 2 | Weak MD5 hashing + hardcoded signing secret | Security | `automation-sandbox/token_utils.py` | Use HMAC-SHA256; read secret from env |
| 3 | `subprocess` `shell=True` command injection + bare `except:` | Security / Quality | `automation-sandbox/file_processor.py` | List-form args, no shell; catch specific exceptions |
| 4 | Unsafe `yaml.load` + mutable default argument | Security / Quality | `automation-sandbox/config_loader.py` | `yaml.safe_load`; default `None` then init |
| 5 | `requests` calls without timeout + `verify=False` | Security | `automation-sandbox/http_client.py` | Add timeouts; enable TLS verification |

## Issue bodies (as filed)

### 1 — [Security] SQL injection in automation-sandbox/user_lookup.py
`get_user_by_username` and `search_users` build SQL by string interpolation of
caller input, allowing SQL injection. Replace with parameterized queries using
`?` placeholders and bound parameters. Add a unit test that a malicious username
(e.g. `' OR '1'='1`) returns no spurious rows.

### 2 — [Security] Weak hashing and hardcoded secret in token_utils.py
`make_token` uses MD5 (cryptographically broken) and a hardcoded
`API_SIGNING_SECRET`. Use `hmac` with SHA-256 and load the secret from an
environment variable. Keep `verify_token` constant-time (`hmac.compare_digest`).

### 3 — [Security/Quality] shell=True command injection and bare except in file_processor.py
`count_lines` runs `subprocess.check_output(cmd, shell=True)` on interpolated
input — command injection. Use list-form arguments without a shell. `safe_read`
uses a bare `except:`; narrow it to `OSError` and stop swallowing
`KeyboardInterrupt`/`SystemExit`.

### 4 — [Security/Quality] Unsafe yaml.load and mutable default arg in config_loader.py
`load_config` calls `yaml.load` without a safe loader (arbitrary object
construction) and uses a mutable default argument `defaults=[]` (shared state
across calls). Switch to `yaml.safe_load` and default to `None`, initializing a
fresh list inside the function.

### 5 — [Security] Missing request timeout and disabled TLS verification in http_client.py
`fetch` and `post_json` issue `requests` calls with no `timeout` (can hang
indefinitely) and `fetch` sets `verify=False` (disables TLS verification). Add
sensible timeouts and remove `verify=False`.

> When GitHub auth is restored these are created via `mcp__github__create_issue`
> (or `gh issue create`) with `labels: ["devin-fix", "security"|"code-quality"]`.
