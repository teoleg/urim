---
paths:
  - "service/**"
  - "api/**"
  - "vercel.json"
  - ".mcp.json"
  - "tools/smoke.py"
---

# Service rules (load when working on REST, MCP or deployment)

## One core, two doors
- REST (`service/app.py`) and MCP (`service/mcp_server.py`) both call `service/core.py`. Put every guardrail in `core.py` so the two can never drift apart.
- Market data only by snapshot ID. Never add a parameter that accepts raw spot/rate/vol.
- The convention pack is required. Never add a default pack.
- Every response includes `service` info with the commit (`VERCEL_GIT_COMMIT_SHA` or `URIM_COMMIT`).

## MCP (mcp SDK 2.x)
- `MCPServer`, not `FastMCP` (renamed in 2.x). Read the installed SDK source when unsure; don't rely on 1.x memory.
- Raise `ToolError` for anticipated refusals so the reason reaches the model; anything else shows only "Error executing tool".
- Streamable HTTP is stateless (serverless) and served at exactly `/mcp`. DNS-rebinding protection stays on; allowed hosts are localhost, Vercel's system hosts and `URIM_ALLOWED_HOSTS`.
- Unknown paths return JSON with the path the app received. Keep that: it is how hosting problems get diagnosed.

## Deployment (Vercel)
- Deploy only via `/deploy` (gate → CLI deploy → `tools/smoke.py`). The `deploy_guard` hook blocks deploying `vercel` commands that skip the gate.
- `vercel.json` settings are not yet verified against Vercel's docs (vercel.com is blocked from this environment). Check the docs before changing them.
- Open issue: the first deployment answered every path with "Not Found"; the next deployment's 404 JSON shows which path Vercel passes to the app.
