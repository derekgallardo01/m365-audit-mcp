"""End-to-end tenant health report — calls all 5 audit tools directly.

The MCP server's purpose is to expose these as agent-callable tools
(Claude Desktop / Cursor / SDK builds). But the underlying audit
functions are pure Python — perfect for a scheduled non-agent script
that builds a tenant health report.

This script:
  1. Calls all 5 audit tools directly (skipping the MCP transport layer)
  2. Cross-references findings (e.g., flagged CA policies + outstanding privacy items)
  3. Builds an executive markdown report
  4. Identifies the top 3 most urgent action items
  5. (Optional) posts the report summary to Slack

The same audit data the MCP server provides to agents, packaged as a
human-readable report for the M365 admin team.

Usage:
    python examples/tenant_health_report.py
    python examples/tenant_health_report.py --markdown report.md
    python examples/tenant_health_report.py --json
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.request
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from m365_audit_mcp import audit_tools  # noqa: E402


def gather_findings() -> dict:
    """Call all 5 audit tools and bundle the results."""
    return {
        "generated_at": datetime.utcnow().isoformat() + "Z",
        "privacy_config": audit_tools.check_tenant_privacy_config(),
        "orphaned_docs": audit_tools.find_orphaned_documents(),
        "conditional_access": audit_tools.audit_conditional_access_policies(),
        "dlp_policies": audit_tools.list_dlp_policies(),
        "copilot_usage": audit_tools.summarize_copilot_usage(),
    }


def derive_top_actions(findings: dict) -> list[str]:
    """Cross-reference findings; surface the highest-priority follow-ups."""
    actions: list[str] = []

    privacy = findings["privacy_config"]
    outstanding = privacy.get("summary", {}).get("items_outstanding", 0)
    if outstanding > 0:
        actions.append(
            f"Close out {outstanding} outstanding privacy-config item(s) — "
            f"required for sign-off before Copilot rollout."
        )

    ca_flagged = findings["conditional_access"].get("count_flagged", 0)
    if ca_flagged > 0:
        actions.append(
            f"Enable {ca_flagged} Conditional Access polic(y/ies) currently in "
            f"report-only mode — security gap until enforced."
        )

    orphans = findings["orphaned_docs"].get("count", 0)
    if orphans >= 2:
        actions.append(
            f"Review {orphans} orphaned SharePoint document(s) — "
            f"each is a potential Copilot grounding leak."
        )

    return actions[:3]  # top 3 only


def render_markdown(findings: dict, top_actions: list[str]) -> str:
    privacy = findings["privacy_config"]
    orphans = findings["orphaned_docs"]
    ca = findings["conditional_access"]
    dlp = findings["dlp_policies"]
    copilot = findings["copilot_usage"]

    lines = [
        f"# M365 Tenant Health Report",
        f"",
        f"_Generated: {findings['generated_at']}_",
        f"_Tenant: {privacy['tenant']['displayName']}_",
        f"",
        f"## Top actions (this week)",
        f"",
    ]
    if top_actions:
        for i, action in enumerate(top_actions, 1):
            lines.append(f"{i}. {action}")
    else:
        lines.append("_No high-priority actions surfaced._")

    lines.extend([
        f"",
        f"## Privacy configuration",
        f"",
        f"- Verified: {privacy['summary']['items_verified']}",
        f"- Outstanding: {privacy['summary']['items_outstanding']}",
        f"- Total items: {privacy['summary']['items_total']}",
        f"",
        f"### Outstanding items",
        f"",
    ])
    outstanding_items = [(k, v) for k, v in privacy["items"].items() if not v.get("verified")]
    if outstanding_items:
        for key, item in outstanding_items:
            lines.append(f"- **{key}**: {item.get('action_required', '(no action note)')}")
    else:
        lines.append("_All items verified._")

    lines.extend([
        f"",
        f"## Orphaned SharePoint documents",
        f"",
        f"- Count: {orphans['count']}",
        f"",
    ])
    if orphans["documents"]:
        lines.append("| Document | Reason | Recommendation |")
        lines.append("|---|---|---|")
        for d in orphans["documents"][:10]:
            lines.append(f"| {d['id']} | {d['reason']} | {d.get('recommendation', '')} |")
    else:
        lines.append("_No orphans._")

    lines.extend([
        f"",
        f"## Conditional Access policies",
        f"",
        f"- Total: {ca['count_total']}",
        f"- Flagged (not enabled): {ca['count_flagged']}",
        f"",
    ])
    if ca.get("flagged"):
        lines.append("### Flagged policies")
        lines.append("")
        lines.append("| Policy | State | Recommendation |")
        lines.append("|---|---|---|")
        for p in ca["flagged"]:
            lines.append(f"| {p['displayName']} | {p['state']} | {p.get('recommendation', '')} |")

    lines.extend([
        f"",
        f"## DLP policies",
        f"",
        f"- Count: {dlp['count']}",
        f"- Locations covered: {sorted(set(loc for p in dlp['policies'] for loc in p['locations']))}",
    ])

    s = copilot["summary"]
    lines.extend([
        f"",
        f"## Copilot adoption",
        f"",
        f"- Tenant active: {s['active_users_total']} of {s['total_users_total']} users "
        f"({s['adoptionPct']}%)",
        f"- Total prompts (30 days): {s['prompts_30d_total']:,}",
        f"- Teams tracked: {s['team_count']}",
        f"",
        f"### Low-adoption teams (< 40%)",
        f"",
    ])
    # adoptionPct in by_team is already a percentage (e.g., 26.7)
    low_teams = [t for t in copilot["by_team"] if t["adoptionPct"] < 40.0]
    if low_teams:
        lines.append("| Team | Active / total | Adoption % |")
        lines.append("|---|---|---|")
        for t in low_teams:
            lines.append(f"| {t.get('displayName', t['team_id'])} | "
                         f"{t['activeUsers']} / {t['totalUsers']} | "
                         f"{t['adoptionPct']:.1f}% |")
    else:
        lines.append("_All teams above 40% adoption._")

    return "\n".join(lines)


def post_to_slack(webhook_url: str, payload: dict) -> int:
    req = urllib.request.Request(
        webhook_url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=10) as resp:
        return resp.status


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="M365 tenant health report from all 5 audit tools.")
    parser.add_argument("--markdown", default=None, help="Write report to this path.")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--slack-webhook", default=os.environ.get("SLACK_WEBHOOK_URL"))
    args = parser.parse_args(argv)

    findings = gather_findings()
    top_actions = derive_top_actions(findings)

    if args.json:
        print(json.dumps({**findings, "top_actions": top_actions},
                          indent=2, default=str))
        return 0

    report = render_markdown(findings, top_actions)
    if args.markdown:
        Path(args.markdown).write_text(report, encoding="utf-8")
        print(f"Wrote markdown report to {args.markdown}")
    else:
        print(report)

    if args.slack_webhook:
        summary = {
            "text": f"M365 Tenant Health Report — {len(top_actions)} action(s) flagged",
            "blocks": [
                {"type": "header", "text": {"type": "plain_text",
                                             "text": "M365 Tenant Health Report"}},
                {"type": "section", "text": {"type": "mrkdwn",
                    "text": "\n".join(f"• {a}" for a in top_actions) or "_No actions._"}},
            ],
        }
        status = post_to_slack(args.slack_webhook, summary)
        print(f"\nSlack notification status: {status}", file=sys.stderr)

    return 0


if __name__ == "__main__":
    sys.exit(main())
