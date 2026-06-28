"""Audit tool implementations.

These are pure Python functions that take primitive arguments and return
JSON-serializable dicts/lists. The MCP server in server.py wraps each as
an MCP tool.

Default backend is the mocked tenant in mock_data.py. To plug in a real
Microsoft Graph backend, replace the module-level `BACKEND` constant with
a Graph client wrapper that returns the same shape. The function bodies
don't change.
"""

from __future__ import annotations

from typing import Any

from . import mock_data

# Backend swap point. In production, replace with a Microsoft Graph client.
BACKEND = mock_data


def check_tenant_privacy_config() -> dict[str, Any]:
    """Return the tenant's privacy / compliance configuration with verification status.

    Mirrors the structure of the m365-privacy-config checklist so the output
    can be pasted straight into a sign-off document.
    """
    cfg = BACKEND.PRIVACY_CONFIG
    tenant = BACKEND.TENANT
    verified = sum(1 for v in cfg.values() if v.get("verified"))
    return {
        "tenant": {
            "id": tenant["id"],
            "displayName": tenant["displayName"],
            "defaultDomain": tenant["defaultDomain"],
            "dataLocation": tenant["dataLocation"],
        },
        "summary": {
            "items_total": len(cfg),
            "items_verified": verified,
            "items_outstanding": len(cfg) - verified,
        },
        "items": cfg,
    }


def find_orphaned_documents(
    days_threshold: int = 180,
    include_no_owner: bool = True,
) -> dict[str, Any]:
    """Return documents that look orphaned.

    A document is orphaned if either:
      - it has no owner (owner is None), OR
      - it hasn't been accessed in `days_threshold` days

    Includes a per-document recommendation (archive / reassign / review).
    """
    out: list[dict[str, Any]] = []
    for doc in BACKEND.DOCUMENTS:
        no_owner = doc.get("owner") is None and include_no_owner
        stale = BACKEND.days_since(doc["lastAccessed"]) > days_threshold
        if not (no_owner or stale):
            continue
        if no_owner:
            reason, action = "no owner", "reassign or archive"
        elif "former" in (doc.get("owner") or ""):
            reason, action = "owner appears to have left the organization", "reassign"
        else:
            reason, action = (
                f"not accessed in {BACKEND.days_since(doc['lastAccessed'])} days",
                "review and archive if obsolete",
            )
        out.append({
            "id": doc["id"],
            "name": doc["name"],
            "site": doc["siteUrl"],
            "owner": doc.get("owner"),
            "lastAccessed": doc["lastAccessed"],
            "sensitivityLabel": doc.get("sensitivityLabel"),
            "reason": reason,
            "recommendedAction": action,
        })
    out.sort(key=lambda d: d["lastAccessed"])
    return {
        "criteria": {
            "days_threshold": days_threshold,
            "include_no_owner": include_no_owner,
        },
        "count": len(out),
        "documents": out,
    }


def audit_conditional_access_policies() -> dict[str, Any]:
    """Return Conditional Access policies with flagged risks.

    A policy is flagged if it is in `reportOnly` or `disabled` state (i.e.
    not actually enforcing). Production tenants should aim for zero policies
    in reportOnly indefinitely.
    """
    policies = BACKEND.CONDITIONAL_ACCESS_POLICIES
    flagged = [p for p in policies if p["state"] != "enabled"]
    return {
        "count_total": len(policies),
        "count_enabled": sum(1 for p in policies if p["state"] == "enabled"),
        "count_flagged": len(flagged),
        "policies": policies,
        "flagged": [
            {
                "id": p["id"],
                "displayName": p["displayName"],
                "state": p["state"],
                "recommendation": (
                    "Promote to enabled - confirm via report-only insights first"
                    if p["state"] == "reportOnly"
                    else "Review - currently disabled"
                ),
            }
            for p in flagged
        ],
    }


def list_dlp_policies(location: str | None = None) -> dict[str, Any]:
    """Return DLP policies, optionally filtered by location (Exchange / SharePoint / etc)."""
    policies = BACKEND.DLP_POLICIES
    if location:
        policies = [p for p in policies if location in p.get("locations", [])]
    return {
        "filter": {"location": location} if location else None,
        "count": len(policies),
        "policies": policies,
    }


def summarize_copilot_usage(team_id: str | None = None) -> dict[str, Any]:
    """Return Copilot usage stats - per team if `team_id` given, otherwise tenant summary.

    Adoption is `activeUsers / totalUsers`. Teams below 50% adoption get an
    `adoptionStatus` of "low" so the audit user can see where rollout has
    stalled.
    """
    usage = BACKEND.COPILOT_USAGE
    if team_id:
        if team_id not in usage:
            return {"error": f"Unknown team_id: {team_id}",
                    "available": list(usage.keys())}
        team = usage[team_id]
        adoption = team["activeUsers"] / team["totalUsers"]
        return {
            "team_id": team_id,
            **team,
            "adoptionPct": round(adoption * 100, 1),
            "adoptionStatus": "low" if adoption < 0.5 else "healthy",
        }
    # tenant summary
    totals = {
        "team_count": len(usage),
        "active_users_total": sum(t["activeUsers"] for t in usage.values()),
        "total_users_total": sum(t["totalUsers"] for t in usage.values()),
        "prompts_30d_total": sum(t["promptsLast30Days"] for t in usage.values()),
    }
    totals["adoptionPct"] = round(
        totals["active_users_total"] / totals["total_users_total"] * 100, 1
    )
    by_team = []
    for tid, t in usage.items():
        adoption = t["activeUsers"] / t["totalUsers"]
        by_team.append({
            "team_id": tid,
            "displayName": t["displayName"],
            "activeUsers": t["activeUsers"],
            "totalUsers": t["totalUsers"],
            "adoptionPct": round(adoption * 100, 1),
            "adoptionStatus": "low" if adoption < 0.5 else "healthy",
        })
    by_team.sort(key=lambda t: t["adoptionPct"])
    return {"summary": totals, "by_team": by_team}
