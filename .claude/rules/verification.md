---
paths:
  - "verification/**"
  - "tests/test_verification.py"
  - ".claude/agents/thummim.md"
  - ".claude/hooks/thummim_blinders.py"
---

# Verification rules (load when near Thummim's territory)

Thummim is the independent verifier: a subagent that never sees the builder's reasoning or the engine's code, and reprices with its own plain-Python closed-form Black-Scholes.

## Builder rule
- **Do not edit anything under `verification/` yourself.** If it looks wrong, delegate to the `thummim` subagent with a minimal prompt that states the symptom, not your reasoning or your code.
- Never loosen a tolerance. A Thummim FAIL is a finding about the engine, not about the verifier.
- Commit Thummim's changes unchanged, and say in the commit message that Thummim wrote them.
- Never create or edit `verification/stamp.json`; only `tools/validate.py` writes it.

## How it is wired
- Agent: `.claude/agents/thummim.md` (fresh context, `omitClaudeMd`, frontmatter hook `thummim_blinders.py` restricting it to the engine CLI and to writing under `verification/`).
- Code: `verification/reference/black_scholes.py` and `verification/verify.py` (exit 1 on any blocking failure). `tests/test_verification.py` makes the verdict part of pytest.

## Blocking checks (v0)
- Engine price matches Thummim's closed form within 1e-8 × max(1, spot).
- Engine time to expiry matches Thummim's own day-count calculation.
- Put-call parity: C − P = S·e^(−qT) − K·e^(−rT).
- No-arbitrage bounds (European, discounted): max(S·e^(−qT) − K·e^(−rT), 0) ≤ call ≤ S·e^(−qT); max(K·e^(−rT) − S·e^(−qT), 0) ≤ put ≤ K·e^(−rT).
- Metadata present; every disclosed convention and every pack/option type the CLI exposes is covered by the reference.

Warning only: Greeks vs. reference.

## Known limit
Agreement is ~1e-14, so the engine is textbook Black-Scholes. A convention error shared by both sides would pass; Thummim's independent protection is its own day count, parity and bounds.
