# Customization

Five things you'll typically tune per deployment.

## 1. Add a new tool

Three places per tool, all small:

**1a.** Add the pure function to [audit_tools.py](../src/m365_audit_mcp/audit_tools.py):

```python
def review_sharepoint_external_sharing(site_url: str | None = None) -> dict:
    """Return external-sharing links across SharePoint."""
    sites = BACKEND.SHAREPOINT_SITES  # add to mock_data.py + Graph backend
    ...
    return {"count": ..., "external_links": [...]}
```

**1b.** Add the MCP-decorated wrapper to [server.py](../src/m365_audit_mcp/server.py):

```python
@mcp.tool()
def review_sharepoint_external_sharing(site_url: str | None = None) -> dict:
    """Return external-sharing links across SharePoint sites.

    Optional site_url filter. Each link includes the recipient domain
    and whether it's permissionless ("anyone with the link") - the
    common audit finding before disabling anonymous sharing tenant-wide.
    """
    return audit_tools.review_sharepoint_external_sharing(site_url=site_url)
```

The docstring on the `server.py` wrapper is what the LLM reads. Write it
for the agent, not the developer.

**1c.** Add at least 1-2 tests to [test_audit_tools.py](../tests/test_audit_tools.py):

```python
def test_external_sharing_filters_by_site_url():
    r = audit_tools.review_sharepoint_external_sharing(site_url="/sites/finance")
    for link in r["external_links"]:
        assert link["site_url"] == "/sites/finance"
```

CI gates the merge. Done.

## 2. Swap the mock backend for Microsoft Graph

The `BACKEND` constant at the top of [audit_tools.py](../src/m365_audit_mcp/audit_tools.py)
is the single integration point. To swap to a real Graph backend:

```python
# audit_tools.py
from .graph_backend import GraphBackend  # new file you write

BACKEND = GraphBackend(
    tenant_id=os.environ["M365_TENANT_ID"],
    client_id=os.environ["M365_APP_ID"],
    client_secret=os.environ["M365_APP_SECRET"],
)
```

Your `GraphBackend` class needs the same module-level attributes
`mock_data` exposes — `TENANT`, `PRIVACY_CONFIG`, `DOCUMENTS`,
`CONDITIONAL_ACCESS_POLICIES`, `DLP_POLICIES`, `COPILOT_USAGE` — populated
from Graph queries instead of constants. Minimum scopes per tool:

| Tool | Graph scope |
|---|---|
| `check_tenant_privacy_config` | `Organization.Read.All` |
| `find_orphaned_documents` | `Sites.Read.All` |
| `audit_conditional_access_policies` | `Policy.Read.All` |
| `list_dlp_policies` | `InformationProtectionPolicy.Read.All` |
| `summarize_copilot_usage` | `Reports.Read.All` |

**Cache aggressively.** Graph quotas are real and audit data doesn't need
sub-second freshness. A 5-15 minute TTL on each call is normal.

## 3. Tighten tool docstrings for your specific LLM

The docstrings on `server.py`'s decorated functions are what the LLM uses
to decide which tool to call. If a particular agent isn't picking the
right tool, the fix is almost always in the docstring, not the
implementation.

Common patterns that help:
- Lead with the *user's question* the tool answers: "Use this when the user asks…"
- Name the data shape returned (helps the LLM compose follow-up calls).
- Mention the optional args + when to use them.

## 4. Add prompts and resources (advanced)

MCP supports three primitive types: `tools`, `prompts`, `resources`. This
server only uses tools. You could add:

- A **prompt** that pre-fills a "monthly M365 audit" workflow:
  ```python
  @mcp.prompt()
  def monthly_audit() -> str:
      return ("Walk the privacy config, list orphaned documents over 6 "
              "months old, audit CA policies, and summarize Copilot usage. "
              "Format as a sign-off document.")
  ```
- A **resource** that exposes the most recent audit run as readable
  content (the LLM can `read_resource` it on demand instead of re-running
  every tool).

Neither is needed for v1 — tools cover the use case. Add when an agent
build asks for them.

## 5. Run on a different transport (HTTP/SSE)

FastMCP supports stdio (default), SSE, and HTTP. To run over HTTP:

```python
# server.py main()
mcp.run(transport="sse", host="0.0.0.0", port=8080)
```

Use this for remote-hosted MCP servers (e.g. an internal-tenant audit
service one team runs that other teams' agents call). For local Claude
Desktop / Cursor use, stick with stdio.

## Validating any change

```bash
python -m pytest -q
python -c "from m365_audit_mcp.server import mcp; assert mcp.name == 'm365-audit'"
```

Both should pass. CI runs the same thing on every push.
