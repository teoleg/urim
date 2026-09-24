# urim

Claude Code plugin (in progress) for building, verifying and running a financial pricing service. v0: European equity option on QuantLib. See `PLAN.md` and `CLAUDE.md`.

```bash
python3 -m venv .venv && .venv/bin/pip install -e ".[dev]"
.venv/bin/python -m pytest -q
.venv/bin/python -m engine.cli price --snapshot tests/golden/snapshots/SYN-EQ-2026-09-24.json \
  --type call --strike 100 --expiry 2027-09-24 --pack EQ-EURO-US-v1
```

Run the service locally (REST + MCP at `/mcp`):

```bash
.venv/bin/uvicorn service.app:app --port 8000
curl -s localhost:8000/price -H 'content-type: application/json' \
  -d '{"snapshot_id":"SYN-EQ-2026-09-24","option_type":"call","strike":100,"expiry":"2027-09-24","pack":"EQ-EURO-US-v1"}'
```

All market data in this repo is synthetic.
