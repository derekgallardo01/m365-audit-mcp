# Evaluation

How to test an MCP server beyond unit tests. The 11 tests in
[tests/test_audit_tools.py](../tests/test_audit_tools.py) cover the
implementation; this doc covers the layers above.

## What the unit tests cover

Each tool function has 2-3 tests:

| Tool | Test focus |
|---|---|
| `check_tenant_privacy_config` | Returns tenant + summary + per-item; counts add up; flags action_required correctly |
| `find_orphaned_documents` | Default flags no-owner + stale; `include_no_owner=False` drops that reason; threshold actually filters |
| `audit_conditional_access_policies` | Flags report-only policies; recommendation text mentions state |
| `list_dlp_policies` | Unfiltered returns all; location filter works |
| `summarize_copilot_usage` | Tenant summary sorted ascending; team detail flags low adoption; unknown team returns useful error |

These are pure-function tests — fast, deterministic, no MCP transport involved.

```bash
python -m pytest -q
# 11 passed in 0.03s
```

CI gates the merge. If you change `mock_data.py`, the tests' baseline
counts may shift — update the test, don't weaken it.

## What the smoke test covers

The CI runs an additional check that the MCP server actually imports
cleanly and registers its tools:

```bash
python -c "
from m365_audit_mcp.server import mcp
assert mcp.name == 'm365-audit'
"
```

If this fails, something about the FastMCP integration broke — usually
either a tool docstring that's now invalid (FastMCP parses them for the
schema), or a tool function whose signature doesn't have type hints
(MCP needs them for the LLM-facing schema).

## What's NOT covered (and why)

- **End-to-end against a real MCP client.** Spinning up Claude Desktop in
  CI is impractical. Local verification works: install + wire into Claude
  Desktop + ask the test question.
- **Microsoft Graph integration.** The mocked backend is the test target;
  a real Graph backend lives in your fork and brings its own tests.
- **Tool selection accuracy.** Whether Claude picks the right tool from a
  natural-language question is the LLM's job, not the server's. The
  server's lever is the docstring quality.

## Pattern when you add a new tool

1. Write the test FIRST (in `tests/test_audit_tools.py`). Failing test
   makes the spec concrete.
2. Implement the function in `audit_tools.py`. Make the test pass.
3. Wrap in `@mcp.tool()` in `server.py`. Write the docstring for the
   LLM, not the developer.
4. Add a manual verification step to the PR description: "called via
   Claude Desktop with the prompt `<question>`; tool was selected
   correctly and produced `<expected shape>`."

## Why not an eval harness like the other kits?

Those kits (rag-over-docs-kit, copilot-studio-support-agent, etc.) run
golden Q&A sets against the kit's own logic. An MCP server's correctness
is "did the tool function return the right data" — which is exactly what
`pytest` covers. The "eval" of tool selection lives in the consumer
(Claude / Cursor / SDK build), not in the server.

If you do want a tool-selection eval, run it where the agent runs (e.g.
against the Anthropic Messages API with this server registered), not in
this repo.

## What an eval set IS NOT

- Not a substitute for reading the agent's actual responses. The tool
  returns structured data; the LLM converts it to prose; the prose is
  what the user reads. Sanity-check it.
- Not a check on Microsoft Graph correctness. The mocked backend is
  intentionally simple; Graph has 50+ years of edge cases. Your Graph
  backend implementation needs its own tests.
