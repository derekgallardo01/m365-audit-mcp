# Changelog

Notable changes to the M365 Audit MCP server. Dates are when the change
landed on `main`.

## 2026-06-28 — Docs, OSS niceties, Docker, devcontainer
- `docs/getting-started.md`, `architecture.md`, `customization.md`,
  `evaluation.md`, `diagrams.md`, `faq.md` — bringing this repo to the
  same documentation bar as the other 10 in the portfolio
- `CONTRIBUTING.md`, `CODE_OF_CONDUCT.md`, `SECURITY.md` — standard OSS
  expectations
- `.github/ISSUE_TEMPLATE/{bug_report,feature_request,config}.yml` +
  `.github/PULL_REQUEST_TEMPLATE.md` — form-style issue + PR templates
- `.github/dependabot.yml` — monthly updates for github-actions
- `CITATION.cff` — citation metadata at v1.0.0
- `.editorconfig` — consistent whitespace across editors
- `Dockerfile` — container image so the server runs without local Python
- `.devcontainer/devcontainer.json` — one-click "Open in Codespaces"
- README badges: CI + License (MIT) + Python (3.10+) + Open in
  Codespaces, plus the Docs nav line below the badges

## 2026-06-28 — Initial public release (v1.0.0)
- FastMCP server with 5 tools: `check_tenant_privacy_config`,
  `find_orphaned_documents`, `audit_conditional_access_policies`,
  `list_dlp_policies`, `summarize_copilot_usage`
- Mocked tenant backend (`mock_data.py`) with realistic shape mirroring
  Microsoft Graph
- Single `BACKEND` constant as the swap point for production Graph
- 11 unit tests covering each tool + edge cases
- CI on Python 3.11 (pytest + import smoke-test)
- `pyproject.toml` with `m365-audit-mcp` script entry
- README explaining install + Claude Desktop wiring
- LICENSE (MIT), .gitignore
