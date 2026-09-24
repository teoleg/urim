# urim

Claude Code plugin (in progress) for building, verifying and running a financial pricing service. v0: European equity option on QuantLib. See `PLAN.md` and `CLAUDE.md`.

```bash
python3 -m venv .venv && .venv/bin/pip install -e ".[dev]"
.venv/bin/python -m pytest -q
.venv/bin/python -m engine.cli price --snapshot tests/golden/snapshots/SYN-EQ-2026-09-24.json \
  --type call --strike 100 --expiry 2027-09-24 --pack EQ-EURO-US-v1
```

All market data in this repo is synthetic.
