"""MCP server entry point.

Run via:
    python -m m365_audit_mcp.server          (after `pip install -e .`)
    m365-audit-mcp                            (after install, via script entry)

Or wire into Claude Desktop / Cursor by adding to the MCP client config:

    {
      "mcpServers": {
        "m365-audit": {
          "command": "m365-audit-mcp"
        }
      }
    }
"""

from __future__ import annotations

from mcp.server.fastmcp import FastMCP

from . import audit_tools

mcp = FastMCP("m365-audit")


@mcp.tool()
def check_tenant_privacy_config() -> dict:
    """Return the tenant's M365 privacy / compliance configuration with verification status.

    Mirrors the structure of the m365-privacy-config checklist (data residency,
    Copilot no-training, Azure OpenAI retention, BAA scope) so the output can be
    pasted straight into a sign-off document for the compliance owner.

    Returns a dict with the tenant metadata, a summary count of verified vs
    outstanding items, and per-item evidence (or `action_required` if not yet
    verified).
    """
    return audit_tools.check_tenant_privacy_config()


@mcp.tool()
def find_orphaned_documents(
    days_threshold: int = 180,
    include_no_owner: bool = True,
) -> dict:
    """Find documents in the tenant that look orphaned.

    A document is flagged if EITHER:
      - it has no owner (when include_no_owner is True), OR
      - it hasn't been accessed in `days_threshold` days.

    Each flagged document includes a recommendation (archive, reassign, or
    review). Useful for monthly governance review or before enabling Copilot
    on a site (orphaned docs leak into Copilot grounding by default).
    """
    return audit_tools.find_orphaned_documents(
        days_threshold=days_threshold,
        include_no_owner=include_no_owner,
    )


@mcp.tool()
def audit_conditional_access_policies() -> dict:
    """Audit Conditional Access policies for risks.

    Lists every CA policy and flags any that aren't in `enabled` state (i.e.
    `reportOnly` or `disabled`). Report-only policies are documented intent
    that isn't actually enforcing; long-lived report-only policies are a
    common audit finding.
    """
    return audit_tools.audit_conditional_access_policies()


@mcp.tool()
def list_dlp_policies(location: str | None = None) -> dict:
    """List Data Loss Prevention (DLP) policies.

    Optional `location` filter (e.g. "Exchange", "SharePoint", "OneDrive",
    "Teams"). Returns the policy id, displayName, state, locations, and
    sensitiveTypes covered. Useful for confirming that the surfaces a
    Copilot or AI build will touch are actually covered before go-live.
    """
    return audit_tools.list_dlp_policies(location=location)


@mcp.tool()
def summarize_copilot_usage(team_id: str | None = None) -> dict:
    """Summarize Microsoft 365 Copilot usage.

    With no arguments, returns a tenant-wide summary plus per-team breakdown
    sorted by adoption percentage (lowest first - the rollout-gap teams).
    With `team_id`, returns the detailed stats + top prompts for that team.

    Adoption is `activeUsers / totalUsers`. Teams below 50% get
    `adoptionStatus: "low"` so the user can see where rollout has stalled.
    """
    return audit_tools.summarize_copilot_usage(team_id=team_id)


def main() -> None:
    """Run the MCP server over stdio (the standard transport for MCP clients)."""
    mcp.run()


if __name__ == "__main__":
    main()
