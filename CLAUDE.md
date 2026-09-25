# CLAUDE.md — Urim

Urim is a Claude Code plugin that lets developers build, verify and run a financial pricing service. The project has two equal goals: learn every Claude Code component by building and using it, and ship the plugin. Full brief and all recorded decisions: `PLAN.md` (read it when a question touches scope, milestones or product decisions).

## Current state

- Milestone: **M6 done locally** (FastAPI + MCP service). Vercel deploy path built; the live deployment answers "Not Found" and needs a routing fix, which needs vercel.com network access and `VERCEL_TOKEN`. Next: M7 plugin packaging.
- v0 slice: **European equity option** (Black-Scholes): market snapshot → price + Greeks → REST + MCP → independent verification.
- Stack: **Python + QuantLib only**. No C++.
- Skills: `market-snapshot`, `conventions`, `add-instrument`. Commands: `/validate`, `/deploy` (user-only), `/new-pricing-service` (user-only). Use them rather than improvising these workflows.

## How we work

- Work milestone by milestone (`PLAN.md` §8). Stop at the end of each milestone for review. Never start the next milestone unasked.
- Commit and push to `main`. Write commit messages to a file and use `git commit -F` (see Hooks).
- Before building any Claude Code component (plugin, skill, hook, subagent, command, MCP server, settings, rule), check the current Claude Code docs for the exact format. Do not rely on memory.
- **Nothing external blocks development.** No licensed data, no outside references, no waiting on third parties. If something external is needed, stub it synthetically and move on.
- Two-way dialog: challenge assumptions and ask when a decision is genuinely the owner's. Record decisions in `PLAN.md` §9.
- The owner is learning Claude Code by using it: explain which component did what, and prefer letting them trigger things over doing everything for them.

## Domain rules (guardrails: refuse, don't work around)

- Never price without a dated, identified market snapshot (snapshot ID + as-of date).
- Never assume conventions silently (day count, calendar, exercise style, settlement). Use a named convention pack and disclose it in the output, or ask.
- Every result carries: market snapshot ID, as-of date, conventions used.
- Never edit validated models (`engine/**/validated/`) without an explicit ADR.
- Never deploy unless golden tests and the Thummim verifier pass.
- Never commit secrets or licensed market data. Snapshots are synthetic (labelled as such) or clearly public.
- Never change a golden expected value to make a test pass. A golden diff is a finding to explain, not a number to update.
- `verification/` belongs to Thummim, the independent verifier subagent. Don't edit it yourself; delegate to the `thummim` agent.

## Area rules (`.claude/rules/`, load when you open matching files)

- `engine.md`: pricer contract, immutable convention packs, instruments, golden freeze.
- `verification.md`: Thummim's territory, builder rule, blocking checks, known limit.
- `service.md`: one core for REST + MCP, MCP SDK 2.x specifics, deployment.

## Hooks (`.claude/settings.json`, scripts in `.claude/hooks/`)

- `protect_paths.py` (PreToolUse): denies edits to `tests/golden/expected/**`, and to `engine/**/validated/**` without an accepted ADR. Its Bash check is crude: a command whose text mentions a protected path must be read-only, so a `git commit -m` naming one is blocked too.
- `deploy_guard.py` (PreToolUse, Bash): deploying `vercel` commands must pass `tools/deploy_gate.py`.
- `test_on_edit.py` (PostToolUse): runs pytest after edits to `engine/`, `tests/`, `tools/`, `pyproject.toml`.
- If a hook blocks you, fix the cause. Do not look for another route around it.

## Commands

```bash
python3 -m venv .venv && .venv/bin/pip install -e ".[dev]"     # setup
.venv/bin/python -m pytest -q                                   # all tests
.venv/bin/python -m engine.cli price --snapshot tests/golden/snapshots/SYN-EQ-2026-09-24.json \
  --type call --strike 100 --expiry 2027-09-24 --pack EQ-EURO-US-v1
.venv/bin/python tools/validate.py                              # tests + Thummim script; writes stamp
.venv/bin/python tools/deploy_gate.py                           # may this commit be deployed?
.venv/bin/uvicorn service.app:app --port 8000                  # REST on :8000, MCP at :8000/mcp
.venv/bin/python tools/smoke.py http://127.0.0.1:8000           # smoke test vs golden values
```

## Layout

```
engine/          # Python + QuantLib: market/ instruments/ conventions/
service/         # FastAPI + MCP over the engine; api/index.py is the Vercel entry
verification/    # Thummim's reference and verify.py
tests/golden/    # frozen synthetic snapshots + expected results
tools/           # validate, deploy gate, smoke, freeze
.claude/         # settings, hooks, rules, skills, agents
plugin/          # (M7) the packaged product
```
