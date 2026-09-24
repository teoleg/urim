---
name: new-pricing-service
description: Stand up a tested, independently verified pricing service for an instrument (v0 supports equity-option). Runs locally only; deploying is a separate /deploy.
disable-model-invocation: true
argument-hint: "[instrument, e.g. equity-option]"
arguments: instrument
allowed-tools: Bash(test *) Bash(ls *)
---

# /new-pricing-service $instrument

Goal (PLAN.md decision 3): when this finishes, the user's repo contains a pricer with invariants and a convention pack, a synthetic market snapshot, green golden tests, a Thummim report, and a service running locally that answers a sample request. It never deploys.

If `$instrument` is empty, ask which instrument. v0 supports `equity-option`.

## Where we are

- Engine present: !`test -d "${CLAUDE_PROJECT_DIR}/engine" && echo yes || echo no`
- Instruments in engine: !`ls "${CLAUDE_PROJECT_DIR}/engine/instruments" 2>/dev/null | grep -v __ || echo none`
- Snapshots: !`ls "${CLAUDE_PROJECT_DIR}/tests/golden/snapshots" 2>/dev/null || echo none`

## Steps

1. **Engine.** If there is no `engine/`: this repo needs the Urim plugin's scaffold, which arrives in milestone M7. Say so and stop.
2. **Instrument.** If `$instrument` is not under `engine/instruments/` (hyphens become underscores), follow the `add-instrument` skill: it has [ASK] gates, so this becomes a conversation, not a one-shot run.
3. **Snapshot.** Make sure at least one validated synthetic snapshot exists for the instrument (the `market-snapshot` skill; validate with its `validate.py`). Never invent market data silently; tell the user every number you chose.
4. **Conventions.** Name the convention pack every price uses and show it to the user (the `conventions` skill).
5. **Verify.** Run `/validate` (the `validate` skill): full tests, Thummim script, Thummim agent review.
6. **Sample price.** Price one sample case through the CLI and show the JSON, including snapshot ID, as-of date and conventions.
7. **Service.** The REST + MCP service arrives in milestone M6. Until then, report this step as "not available yet (M6)"; do not improvise a server.

## Finish

A short checklist of the six deliverables above, each marked done, missing, or not available yet, with file paths. Remind the user that deploying is a separate `/deploy`, which will refuse until everything is committed and validated.
