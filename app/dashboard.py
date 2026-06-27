"""Render a tiny, dependency-free HTML dashboard from the run store."""
from __future__ import annotations

import html
from typing import Any

_STATUS_COLORS = {
    "queued": "#6b7280",
    "active": "#2563eb",
    "done": "#16a34a",
    "error": "#dc2626",
}
_RESULT_COLORS = {"success": "#16a34a", "failure": "#dc2626", None: "#6b7280"}


def render(metrics: dict[str, Any], runs: list[dict[str, Any]]) -> str:
    rate = metrics["success_rate"]
    rate_str = f"{rate * 100:.0f}%" if rate is not None else "—"
    cards = "".join(
        _card(label, value)
        for label, value in [
            ("Total runs", metrics["total"]),
            ("Active", metrics["active"]),
            ("Succeeded", metrics["success"]),
            ("Failed", metrics["failure"]),
            ("Success rate", rate_str),
            ("Avg resolve (s)", metrics["avg_resolution_seconds"]),
        ]
    )
    rows = "".join(_row(r) for r in runs) or (
        "<tr><td colspan='6' style='padding:24px;text-align:center;color:#6b7280'>"
        "No runs yet — label an issue <code>devin-fix</code> to start.</td></tr>"
    )
    return _TEMPLATE.format(cards=cards, rows=rows)


def _card(label: str, value: Any) -> str:
    return (
        f"<div class='card'><div class='card-v'>{html.escape(str(value))}</div>"
        f"<div class='card-l'>{html.escape(label)}</div></div>"
    )


def _row(r: dict[str, Any]) -> str:
    status = r["status"]
    result = r.get("result")
    sc = _STATUS_COLORS.get(status, "#6b7280")
    rc = _RESULT_COLORS.get(result, "#6b7280")
    issue_link = f"https://github.com/{r['repo']}/issues/{r['issue_number']}"
    session = (
        f"<a href='{html.escape(r['session_url'])}' target='_blank'>session</a>"
        if r.get("session_url") else "—"
    )
    pr = (
        f"<a href='{html.escape(r['pr_url'])}' target='_blank'>PR ↗</a>"
        if r.get("pr_url") else "—"
    )
    return (
        "<tr>"
        f"<td><a href='{issue_link}' target='_blank'>#{r['issue_number']}</a></td>"
        f"<td>{html.escape(r['issue_title'])}</td>"
        f"<td><span class='pill' style='background:{sc}'>{html.escape(status)}</span></td>"
        f"<td><span class='pill' style='background:{rc}'>{html.escape(str(result or '—'))}</span></td>"
        f"<td>{session}</td>"
        f"<td>{pr}</td>"
        "</tr>"
    )


_TEMPLATE = """<!doctype html>
<html><head><meta charset="utf-8"><title>Devin Remediation Dashboard</title>
<meta http-equiv="refresh" content="10">
<style>
 body{{font-family:-apple-system,Segoe UI,Roboto,sans-serif;margin:0;background:#f8fafc;color:#0f172a}}
 header{{background:#0f172a;color:#fff;padding:20px 32px}}
 header h1{{margin:0;font-size:20px}} header p{{margin:4px 0 0;color:#94a3b8;font-size:13px}}
 .cards{{display:flex;gap:16px;flex-wrap:wrap;padding:24px 32px}}
 .card{{background:#fff;border:1px solid #e2e8f0;border-radius:12px;padding:16px 20px;min-width:120px}}
 .card-v{{font-size:28px;font-weight:700}} .card-l{{font-size:12px;color:#64748b;margin-top:4px}}
 table{{width:calc(100% - 64px);margin:0 32px 32px;border-collapse:collapse;background:#fff;
   border:1px solid #e2e8f0;border-radius:12px;overflow:hidden}}
 th,td{{text-align:left;padding:12px 16px;font-size:14px;border-bottom:1px solid #f1f5f9}}
 th{{background:#f8fafc;color:#475569;font-size:12px;text-transform:uppercase;letter-spacing:.04em}}
 .pill{{color:#fff;padding:2px 10px;border-radius:999px;font-size:12px}}
 a{{color:#2563eb;text-decoration:none}}
</style></head>
<body>
 <header><h1>Devin Remediation Dashboard</h1>
 <p>Event-driven Superset issue remediation · auto-refreshes every 10s</p></header>
 <div class="cards">{cards}</div>
 <table><thead><tr>
   <th>Issue</th><th>Title</th><th>Status</th><th>Result</th><th>Devin</th><th>PR</th>
 </tr></thead><tbody>{rows}</tbody></table>
</body></html>"""
