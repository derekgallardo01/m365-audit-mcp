# syntax=docker/dockerfile:1
FROM python:3.11-slim

WORKDIR /app
COPY . .

RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -e . && \
    pip install --no-cache-dir pytest

# Default: run the MCP server over stdio. To run tests instead, override
# the command:
#   docker run --rm <image> python -m pytest -q
#
# Note: stdio servers expect to be launched by a parent MCP client. For
# Claude Desktop / Cursor integration, prefer `pip install -e .` on the
# host and point the MCP client at the `m365-audit-mcp` script entry. This
# Dockerfile is for CI, packaging, and remote-hosted deployments.
CMD ["m365-audit-mcp"]
