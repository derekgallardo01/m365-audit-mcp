# Getting started

A 5-minute walkthrough — install the server, wire it into Claude Desktop,
and ask the first question.

## 1. Clone and install

```bash
git clone https://github.com/derekgallardo01/m365-audit-mcp.git
cd m365-audit-mcp
pip install -e .
```

Verify the install:

```bash
m365-audit-mcp --help    # if --help isn't supported, it'll just hang waiting for stdio - Ctrl-C is fine
```

## 2. Run the tests

```bash
pip install pytest
python -m pytest -q
```

`11 passed in 0.03s`. The tests exercise each of the 5 tools' pure-function
implementations directly — they don't go through MCP transport, which is
how they stay fast.

## 3. Wire into Claude Desktop

Open Claude Desktop's MCP config (Settings → Developer → Edit Config):

```json
{
  "mcpServers": {
    "m365-audit": {
      "command": "m365-audit-mcp"
    }
  }
}
```

Restart Claude Desktop. The 5 tools appear in the tool list. Test it:

> *"Summarize our M365 tenant's privacy configuration and flag anything
> outstanding."*

Claude calls `check_tenant_privacy_config`, gets the structured response,
and answers in natural language with the items flagged for action. No
prompt engineering required — the tool docstrings are the prompt.

## 4. Wire into Cursor / other MCP clients

Same JSON config shape. Cursor: `~/.cursor/mcp.json`. The `command` field
points at the `m365-audit-mcp` script entry installed by `pip install -e .`.

## 5. Try without installing — run from source

```bash
python -m m365_audit_mcp.server
```

Then point your MCP client at this command instead of the script entry.
Useful for development against the source.

## What to read next

- [Architecture](architecture.md) — components + flow + Microsoft Graph swap point
- [Diagrams](diagrams.md) — additional sequence, state, and decision diagrams
- [Customization](customization.md) — adding a new tool, swapping the backend
- [Evaluation](evaluation.md) — testing pattern for MCP tools
- [FAQ](faq.md) — common questions

## Bringing it to a real tenant

The mocked backend is a single substitution point. See
[customization.md §2](customization.md#2-swap-the-mock-backend-for-microsoft-graph)
for the production swap.
