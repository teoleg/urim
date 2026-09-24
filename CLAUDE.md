# CLAUDE.md — Urim

Urim is a Claude Code plugin that lets developers build, verify and run a financial pricing service. The project has two equal goals: learn every Claude Code component by building and using it, and ship the plugin. Full brief and all recorded decisions: `PLAN.md` (read it when a question touches scope, milestones or product decisions).

## Current state

- Milestone: **M3 done** (Thummim verifier), awaiting review. Next: M4 domain skills.
- v0 slice: **European equity option** (Black-Scholes) — market snapshot → price + Greeks → REST + MCP → independent verification.
- Stack: **Python + QuantLib only**. No C++.

## How we work

- Work milestone by milestone (`PLAN.md` §8). Stop at the end of each milestone for review. Never start the next milestone unasked.
- Commit and push to `main`.
- Before building any Claude Code component (plugin, skill, hook, subagent, command, MCP server, settings), check the current Claude Code docs for the exact format. Do not rely on memory.
- **Nothing external blocks development.** No licensed data, no outside references, no waiting on third parties. If something external is needed, stub it synthetically and move on.
- Two-way dialog: challenge assumptions and ask when a decision is genuinely the owner's. Record decisions in `PLAN.md` §9.

## Commands

```bash
python3 -m venv .venv && .venv/bin/pip install -e ".[dev]"     # setup
.venv/bin/python -m pytest -q                                   # all tests
.venv/bin/python -m engine.cli price --snapshot tests/golden/snapshots/SYN-EQ-2026-09-24.json \
  --type call --strike 100 --expiry 2027-09-24 --pack EQ-EURO-US-v1
.venv/bin/python tools/freeze_golden.py SNAPSHOT_ID             # one-way; refuses to overwrite
.venv/bin/python verification/verify.py                         # Thummim's checks; writes verification/report.md
```

Golden expected values in M1 are a regression freeze made by the engine itself, not an independent proof.

## Hooks (`.claude/settings.json`, scripts in `.claude/hooks/`)

- `protect_paths.py` (PreToolUse, Edit|Write|NotebookEdit|Bash): denies edits to `tests/golden/expected/**`; denies `engine/**/validated/**` unless an ADR in `docs/adr/` has `Status: Accepted` and names the path. Fails closed.
- The Bash part is best effort and crude: any command whose text mentions a protected path must be a known read-only command. It is not a sandbox, and it also blocks harmless commands (e.g. a `git commit -m` whose message names a protected path). Write commit messages to a file and use `git commit -F`.
- `test_on_edit.py` (PostToolUse, Edit|Write): runs pytest after edits to `engine/`, `tests/`, `tools/`, `pyproject.toml`; failures come back to Claude as a block reason. Does not fire for files changed via Bash.
- If a hook blocks you, fix the cause. Do not look for another route around it.

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

- Subagent: `.claude/agents/thummim.md` (fresh context, `omitClaudeMd`, frontmatter hook `thummim_blinders.py`: engine is a black box via its CLI; writes only under `verification/`).
- Its code: `verification/reference/black_scholes.py`, `verification/verify.py` (exit 1 on any blocking failure). `tests/test_verification.py` makes its verdict part of pytest.
- **Builder rule:** don't edit `verification/` yourself. If it looks wrong, delegate to Thummim with a minimal prompt that states the symptom, not your reasoning.
- Limit: the closed form agrees with QuantLib to ~1e-14, so a convention error shared by both would pass. Thummim's independent protection is its own day-count calculation, parity and bounds.

Blocking invariants (v0):
- QuantLib price matches the independent closed form within tolerance.
- Put-call parity: C − P = S·e^(−qT) − K·e^(−rT).
- No-arbitrage bounds (European): max(S·e^(−qT) − K·e^(−rT), 0) ≤ call ≤ S·e^(−qT); max(K·e^(−rT) − S·e^(−qT), 0) ≤ put ≤ K·e^(−rT). Undiscounted intrinsic is *not* a lower bound for European options.
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
