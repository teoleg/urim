# CLAUDE.md — Urim

Urim is a Claude Code plugin that lets developers build, verify and run a financial pricing service. The project has two equal goals: learn every Claude Code component by building and using it, and ship the plugin. Full brief and all recorded decisions: `PLAN.md` (read it when a question touches scope, milestones or product decisions).

## Current state

- Milestone: **M0** (repo + PLAN.md + CLAUDE.md). Nothing is scaffolded yet.
- v0 slice: **European equity option** (Black-Scholes) — market snapshot → price + Greeks → REST + MCP → independent verification.
- Stack: **Python + QuantLib only**. No C++.

## How we work

- Work milestone by milestone (`PLAN.md` §8). Stop at the end of each milestone for review. Never start the next milestone unasked.
- Commit and push to `main`.
- Before building any Claude Code component (plugin, skill, hook, subagent, command, MCP server, settings), check the current Claude Code docs for the exact format. Do not rely on memory.
- **Nothing external blocks development.** No licensed data, no outside references, no waiting on third parties. If something external is needed, stub it synthetically and move on.
- Two-way dialog: challenge assumptions and ask when a decision is genuinely the owner's. Record decisions in `PLAN.md` §9.

## Domain rules (guardrails — refuse, don't work around)

- Never price without a dated, identified market snapshot (snapshot ID + as-of date).
- Never assume conventions silently (day count, calendar, exercise style, settlement). Use a named convention pack and disclose it in the output, or ask.
- Every result carries: market snapshot ID, as-of date, conventions used.
- Never edit validated models (`engine/**/validated/`) without an explicit ADR.
- Never deploy unless golden tests and the Thummim verifier pass.
- Never commit secrets or licensed market data. Snapshots are synthetic (labelled as such) or clearly public.
- Never change a golden expected value to make a test pass. A golden diff is a finding to explain, not a number to update.

## Verification (Thummim)

Thummim is the independent verifier: it does not see the builder's reasoning and reprices with a different method (plain-Python closed-form Black-Scholes, no QuantLib).

Blocking invariants (v0):
- QuantLib price matches the independent closed form within tolerance.
- Put-call parity: C − P = S·e^(−qT) − K·e^(−rT).
- No-arbitrage bounds: intrinsic ≤ price ≤ spot (call) / ≤ discounted strike (put).
- Monotonicity: price non-decreasing in vol; calls non-decreasing in expiry when q = 0, r ≥ 0.
- Golden tests: frozen snapshot → frozen expected outputs; any diff fails.
- Snapshot ID, as-of date and conventions present on every result.

Warning only (v0): Greeks vs. bump-and-reprice. Promote to blocking once tolerances are calibrated.

## Planned layout

```
plugin/          # the product: skills, commands, agents, hooks, .mcp.json
engine/          # Python + QuantLib: market/ instruments/ risk/ conventions/
service/         # FastAPI + MCP endpoint over engine
tests/golden/    # frozen market snapshots + expected results
```

An instrument is one pluggable unit: pricer + invariants + golden tests + convention pack.
