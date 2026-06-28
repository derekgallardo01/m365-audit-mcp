# FAQ

## Why MCP and not just a REST API?

A REST API would work too — but every MCP client (Claude Desktop, Cursor,
VS Code, Agent SDK builds) speaks MCP natively. The reusable surface
"this server exposes tools any LLM agent can call" is what makes the
asset valuable beyond a single integration. A REST API would need each
of those clients to wrap it manually.

## Do I need a real M365 tenant to use this?

No. The default backend is `mock_data.py` — realistic tenant-shaped
constants. The server runs anywhere with zero credentials. To bring it
to production data, replace the `BACKEND` constant per
[customization.md §2](customization.md#2-swap-the-mock-backend-for-microsoft-graph).

## Why not include a Microsoft Graph backend out of the box?

Three reasons:
1. Graph credentials are per-tenant — the demo would only work for me.
2. A real Graph backend needs caching, error handling, scope management,
   and observability — all of which is your decision per deployment.
3. Demonstrating the *swap point* (one constant) is more valuable
   pedagogically than shipping one specific Graph implementation.

The README and `customization.md` document the swap explicitly so the
production path is unambiguous.

## What's the difference between this and Copilot Studio?

Opposite directions:
- **Copilot Studio** = an agent that lives INSIDE M365. Users interact
  with it via Teams / Copilot Chat. It uses M365 data via Microsoft Graph
  natively.
- **m365-audit-mcp** = an MCP server that SERVES M365 data to an agent
  OUTSIDE M365 (Claude Desktop, Cursor, custom builds). The agent is
  the M365 admin's existing AI tool, not a new one inside the tenant.

Different audiences. Both can live alongside each other.

## How is this different from the m365-privacy-config repo?

`m365-privacy-config` is the human-readable checklist a consultant walks
with the IT/compliance team. `m365-audit-mcp` is the same checks
*automated as tools* the consultant's AI agent can call to verify the
config in seconds rather than minutes. The mocked data here intentionally
mirrors the structure of the checklist items so the output can be pasted
into the same sign-off doc.

## Will the tools work with non-Claude MCP clients?

Yes. MCP is a transport-level protocol; the tools are model-agnostic.
The docstrings are written for an LLM consumer in general (not specifically
Claude). Cursor, custom Agent SDK builds, and any future MCP client work
the same way.

## How do I add prompts or resources?

MCP supports three primitive types: tools, prompts, resources. This
server uses only tools. To add a prompt or resource, see
[customization.md §4](customization.md#4-add-prompts-and-resources-advanced).
Neither was needed for v1.

## What about authentication for the user's M365 tenant?

The mocked default has no auth (it's local data). A production Graph
backend uses an Entra ID app registration with delegated or
application-level scopes (the minimums per tool are in
[customization.md §2](customization.md#2-swap-the-mock-backend-for-microsoft-graph)).
If you need per-end-user OAuth (vs. app-only), that's a vault/MCP-OAuth
pattern that lives outside this server.

## Is the mocked data realistic?

Realistic enough to demo agent behaviour: items are shaped like Graph
responses, time fields use ISO 8601, IDs look right. The values
themselves are made up (`Acme Manufacturing`, fake user emails) so
nothing can be mistaken for a real tenant. Adjust freely for your demo.

## How do I add a 6th tool?

Three small additions — one pure function in `audit_tools.py`, one
`@mcp.tool()` wrapper in `server.py`, one test class in
`test_audit_tools.py`. Pattern matches `summarize_copilot_usage`.
Full walkthrough in [customization.md §1](customization.md#1-add-a-new-tool).

## What does the server actually run? Should it be in Docker?

It runs over stdio — i.e. the MCP client launches it as a subprocess and
talks to it via pipes. The Dockerfile is included for portability
(some teams package MCP servers as container images for distribution),
but for Claude Desktop on a laptop the `pip install -e .` + script entry
is the standard path.
