---
name: conventions
description: Choose, disclose, or add market conventions (day count, calendar, exercise style, compounding, settlement) via named convention packs. Use whenever pricing needs conventions, a user states or omits a convention, results must disclose conventions, or code in engine/conventions/ changes.
when_to_use: "which day count", "what calendar", "ACT/360 or ACT/365", "add a convention pack", "price this option" when the user did not name a pack
allowed-tools: Bash(*list_packs.py*)
paths:
  - "engine/conventions/**"
  - "engine/instruments/**"
---

# Convention packs

Urim never assumes a convention. Every price is computed under a **named, versioned convention pack**, and every result discloses the full pack.

## Packs that exist right now

!`"${CLAUDE_PROJECT_DIR}/.venv/bin/python" "${CLAUDE_SKILL_DIR}/list_packs.py" || echo "(could not list packs: set up .venv first, then read PACKS in engine/conventions/packs.py)"`

## Choosing a pack

1. If the user named a pack, use it exactly.
2. If they didn't, propose the pack that fits and **say so in the answer**: "Priced under EQ-EURO-US-v1 (ACT/365F, NYSE calendar, European, continuous rates)." Never pick one silently.
3. If the user states a convention that differs from every pack (e.g. ACT/360, or a non-NYSE calendar), do **not** quietly price under the nearest pack. Say which field differs and either add a new pack (below) or ask.
4. Expiries that are not business days in the pack's calendar are refused by the engine. Ask the user for a business-day expiry; never roll the date yourself.

## Adding or changing a pack

- **Packs are immutable once used.** Golden values and past results depend on them. To change anything, add a new pack with a bumped version (`EQ-EURO-US-v2`), never edit `v1`.
- Name: `<ASSETCLASS>-<EXERCISE>-<MARKET>-v<N>`.
- Add it to `PACKS` in `engine/conventions/packs.py`. Every field must be filled in words a reviewer can check; no "default" or "standard" without saying what it is.
- If it needs a day count or calendar that isn't mapped yet, extend `_DAY_COUNTS` / `_CALENDARS` with the exact QuantLib object, and add a test that the name maps to the object you intended.
- Add a test that a result priced under the new pack discloses it (`result.conventions == pack.to_dict()`).
- Tell Thummim (the verifier) about the new pack only through what the engine discloses. If the new pack uses a day count Thummim's reference doesn't support, Thummim should fail it as blocking; that is correct behaviour, not a bug to work around. Ask Thummim to extend its reference.

## Common traps (state them, don't absorb them)

- ACT/365F vs ACT/360: a 1-year option differs by about 1.4% in time, which is not a rounding error.
- Rates quoted annually compounded vs continuous: convert explicitly (`r_cont = ln(1 + r_annual)`) and write the conversion into the snapshot's `source`.
- Vol quoted in percent vs decimal.
- Business-day calendar vs calendar days for time to expiry: the pack's day count decides T, the calendar only decides valid dates.
