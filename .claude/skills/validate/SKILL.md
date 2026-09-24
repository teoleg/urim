---
name: validate
description: Run the full Urim validation - test suite, Thummim's verify script, and an independent Thummim agent review - and record a validation stamp for the current commit. Use before any deploy, after engine or golden changes, or when asked whether the numbers are verified.
allowed-tools: Bash(*tools/validate.py*) Bash(git -C *)
---

# /validate

Produce evidence, not an opinion. Two independent parts must both pass.

## Current state

- HEAD: !`git -C "${CLAUDE_PROJECT_DIR}" rev-parse --short HEAD`
- Uncommitted changes: !`git -C "${CLAUDE_PROJECT_DIR}" status --porcelain | head -20`

## 1. Scripted checks

Run `.venv/bin/python tools/validate.py`. It runs the full test suite (which includes Thummim's `verification/verify.py`) and, only if everything passes, writes `verification/stamp.json` tied to the current commit. Report its final `VALIDATION:` line and any failures verbatim.

If it fails: stop. Show the failing output. Do not fix anything as part of /validate, and never edit tolerances, golden values or anything under `verification/`.

## 2. Independent review by Thummim

Launch the **thummim** subagent (Agent tool, `subagent_type: thummim`) with exactly this prompt, adding nothing about the implementation, your reasoning or your doubts:

> Re-verify the engine. First check that your reference and verify.py cover every instrument, option type and convention pack that the engine CLI and the golden cases currently expose; extend them if not. Then run verify.py and report your verdict.

If Thummim returns anything other than `VERDICT: PASS`, run `.venv/bin/python tools/validate.py --invalidate` so no stamp survives, and report its findings.

## 3. Report

One short block:
- `VALIDATION: PASS` or `FAIL`, commit, and whether the tree was clean
- tests: pass/fail count; Thummim script: pass/fail; Thummim agent: verdict + any warnings
- if the tree was dirty: say that `/deploy` will refuse until the changes are committed and `/validate` is run again
