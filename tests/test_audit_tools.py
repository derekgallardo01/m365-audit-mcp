"""Tests for the audit tool implementations.

Tests don't touch the MCP transport layer - they exercise the pure functions
in audit_tools.py directly. That keeps the test suite fast and the
implementation honest (the MCP server in server.py is a thin wrapper).
"""

import sys
import os

# Make the src/ package importable without a build step.
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from m365_audit_mcp import audit_tools  # noqa: E402


def test_privacy_config_returns_tenant_and_summary():
    r = audit_tools.check_tenant_privacy_config()
    assert "tenant" in r and "summary" in r and "items" in r
    assert r["tenant"]["displayName"] == "Acme Manufacturing"
    s = r["summary"]
    assert s["items_total"] == s["items_verified"] + s["items_outstanding"]
    assert s["items_outstanding"] >= 1  # the AOAI retention row is intentionally not verified


def test_privacy_config_flags_action_required():
    r = audit_tools.check_tenant_privacy_config()
    aoai = r["items"]["azure_openai_no_retention"]
    assert aoai["verified"] is False
    assert "action_required" in aoai


def test_orphaned_documents_default_finds_no_owner_and_stale():
    r = audit_tools.find_orphaned_documents()
    assert r["count"] >= 2  # the orphaned board minutes + the former-employee marketing plan
    by_id = {d["id"]: d for d in r["documents"]}
    assert "doc-002" in by_id  # no owner
    assert by_id["doc-002"]["reason"] == "no owner"


def test_orphaned_documents_include_no_owner_false_drops_that_reason():
    # When include_no_owner=False, no document should be flagged FOR the
    # no-owner reason. A no-owner doc that is ALSO stale still gets flagged
    # for staleness (correct behaviour - it's still orphaned in practice).
    r = audit_tools.find_orphaned_documents(include_no_owner=False)
    for d in r["documents"]:
        assert d["reason"] != "no owner"


def test_orphaned_documents_threshold_changes_count():
    tight = audit_tools.find_orphaned_documents(days_threshold=30)
    loose = audit_tools.find_orphaned_documents(days_threshold=10000)
    assert tight["count"] >= loose["count"]


def test_conditional_access_flags_report_only_policies():
    r = audit_tools.audit_conditional_access_policies()
    assert r["count_flagged"] >= 1  # block-legacy-auth is in reportOnly
    flagged_ids = {p["id"] for p in r["flagged"]}
    assert "ca-003" in flagged_ids
    rec = next(p for p in r["flagged"] if p["id"] == "ca-003")["recommendation"]
    assert "report-only" in rec.lower() or "enabled" in rec.lower()


def test_dlp_policies_unfiltered_returns_all():
    r = audit_tools.list_dlp_policies()
    assert r["filter"] is None
    assert r["count"] >= 2


def test_dlp_policies_filter_by_location():
    r = audit_tools.list_dlp_policies(location="Exchange")
    for p in r["policies"]:
        assert "Exchange" in p["locations"]
    assert r["filter"] == {"location": "Exchange"}


def test_copilot_usage_tenant_summary_sorts_by_adoption_ascending():
    r = audit_tools.summarize_copilot_usage()
    pcts = [t["adoptionPct"] for t in r["by_team"]]
    assert pcts == sorted(pcts)  # lowest adoption first
    assert r["summary"]["team_count"] == len(r["by_team"])


def test_copilot_usage_flags_low_adoption_team():
    r = audit_tools.summarize_copilot_usage(team_id="team-clinical")
    assert r["adoptionStatus"] == "low"  # 12/45 = 26.7%
    assert "topPrompts" in r


def test_copilot_usage_unknown_team_returns_error_with_available_list():
    r = audit_tools.summarize_copilot_usage(team_id="team-does-not-exist")
    assert "error" in r
    assert "available" in r
    assert "team-clinical" in r["available"]
