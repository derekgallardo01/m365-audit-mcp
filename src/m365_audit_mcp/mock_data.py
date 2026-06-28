"""Realistic-looking mocked M365 tenant data.

The shape of every return value matches what the equivalent Microsoft Graph
endpoint would return - so swapping `mock_data` for a real Graph client is
a single substitution (see audit_tools.py for the seam).
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

TENANT = {
    "id": "fc8e0a3d-1234-4567-8901-abcdef123456",
    "displayName": "Acme Manufacturing",
    "defaultDomain": "acmemfg.onmicrosoft.com",
    "dataLocation": {"region": "United States", "geo": "us"},
}

# Privacy / compliance configuration as it would appear after walking the
# privacy-config-checklist (the sibling repo). Each entry mirrors a checklist
# row so the audit_tools function can report the same fields verbatim.
PRIVACY_CONFIG = {
    "data_residency": {
        "verified": True,
        "region": "United States",
        "evidence": "M365 admin center -> Organization profile -> Data location (verified 2026-06-20)",
    },
    "copilot_no_public_training": {
        "verified": True,
        "source": "Microsoft Product Terms (DPA) + Copilot data-handling article",
        "retrieved": "2026-06-20",
    },
    "azure_openai_no_retention": {
        "verified": False,
        "reason": "no-retention option not yet requested from Microsoft",
        "action_required": "Submit Modified Content Filtering + no-retention request via Microsoft account team",
    },
    "baa_in_scope": {
        "verified": True,
        "agreement": "Microsoft BAA signed 2024-03, renewed 2026-03",
        "services_covered": ["Exchange", "SharePoint", "OneDrive", "Teams", "M365 Copilot"],
    },
}

CONDITIONAL_ACCESS_POLICIES = [
    {
        "id": "ca-001",
        "displayName": "Require MFA for all users",
        "state": "enabled",
        "conditions": {"users": "All users", "applications": "All cloud apps"},
        "grantControls": ["mfa"],
    },
    {
        "id": "ca-002",
        "displayName": "Require compliant device for PHI access",
        "state": "enabled",
        "conditions": {
            "users": "PHI-Authorized-Users",
            "applications": "SharePoint sites tagged PHI",
        },
        "grantControls": ["compliantDevice", "domainJoinedDevice"],
    },
    {
        "id": "ca-003",
        "displayName": "Block legacy authentication",
        "state": "reportOnly",  # not yet enforced
        "conditions": {"users": "All users", "clientAppTypes": ["other"]},
        "grantControls": ["block"],
    },
]

DLP_POLICIES = [
    {
        "id": "dlp-pii-us",
        "displayName": "PII (US) - SSN + DOB + Credit Card",
        "state": "enabled",
        "locations": ["Exchange", "SharePoint", "OneDrive", "Teams"],
        "sensitiveTypes": ["U.S. Social Security Number", "Credit Card Number", "U.S. Date of Birth"],
    },
    {
        "id": "dlp-phi",
        "displayName": "PHI - Medical Record Numbers + ICD codes",
        "state": "enabled",
        "locations": ["SharePoint", "OneDrive", "Teams"],
        "sensitiveTypes": ["U.S. Medical Record Number", "ICD-10 codes"],
    },
]

# Mock document inventory across two sample SharePoint sites.
DOCUMENTS = [
    {
        "id": "doc-001",
        "name": "Code of Conduct.docx",
        "siteUrl": "/sites/policies",
        "owner": "a.okafor@acmemfg.com",
        "lastModified": "2026-04-15T10:23:00Z",
        "lastAccessed": "2026-06-25T14:01:00Z",
        "sensitivityLabel": "Confidential - Internal",
    },
    {
        "id": "doc-002",
        "name": "Q1 Board Minutes 2024.docx",
        "siteUrl": "/sites/board",
        "owner": None,  # orphaned
        "lastModified": "2024-03-12T09:00:00Z",
        "lastAccessed": "2024-08-02T11:14:00Z",  # >1 year ago
        "sensitivityLabel": "Confidential - Board Only",
    },
    {
        "id": "doc-003",
        "name": "Patient Intake Form Template.xlsx",
        "siteUrl": "/sites/clinical",
        "owner": "m.lin@acmemfg.com",
        "lastModified": "2026-06-10T15:45:00Z",
        "lastAccessed": "2026-06-27T08:30:00Z",
        "sensitivityLabel": "Highly Confidential - PHI",
    },
    {
        "id": "doc-004",
        "name": "Legacy Marketing Plan 2022.pptx",
        "siteUrl": "/sites/marketing",
        "owner": "former.employee@acmemfg.com",  # employee left
        "lastModified": "2022-11-08T16:20:00Z",
        "lastAccessed": "2023-02-14T10:45:00Z",
        "sensitivityLabel": "General",
    },
    {
        "id": "doc-005",
        "name": "Vendor Contracts Master.xlsx",
        "siteUrl": "/sites/finance",
        "owner": "l.tan@acmemfg.com",
        "lastModified": "2026-06-27T17:00:00Z",
        "lastAccessed": "2026-06-28T08:00:00Z",
        "sensitivityLabel": "Confidential - Internal",
    },
]

# Mocked Copilot usage stats per team.
COPILOT_USAGE = {
    "team-marketing": {
        "displayName": "Marketing",
        "activeUsers": 24,
        "totalUsers": 28,
        "promptsLast30Days": 1247,
        "topPrompts": [
            "Draft a campaign brief for Q3 product launch",
            "Summarize the Q2 marketing performance",
            "Brainstorm hook lines for the LinkedIn post about new feature X",
        ],
    },
    "team-clinical": {
        "displayName": "Clinical Operations",
        "activeUsers": 12,
        "totalUsers": 45,  # low adoption - opportunity
        "promptsLast30Days": 89,
        "topPrompts": [
            "Summarize this patient intake form (PII redacted)",
            "Draft a follow-up email for missed appointments",
        ],
    },
    "team-engineering": {
        "displayName": "Engineering",
        "activeUsers": 18,
        "totalUsers": 22,
        "promptsLast30Days": 2103,
        "topPrompts": [
            "Explain this code snippet",
            "Generate unit tests for the function",
            "Refactor this method for readability",
        ],
    },
}


def _utc_days_ago(days: int) -> datetime:
    return datetime.now(timezone.utc) - timedelta(days=days)


def days_since(iso_ts: str) -> int:
    """Days between now and an ISO 8601 timestamp."""
    ts = datetime.fromisoformat(iso_ts.replace("Z", "+00:00"))
    return (datetime.now(timezone.utc) - ts).days
