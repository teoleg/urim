---
name: deploy
description: Deploy the Urim pricing service. Refuses unless tests and Thummim passed on exactly the commit being deployed.
disable-model-invocation: true
allowed-tools: Bash(*tools/deploy_gate.py*)
---

# /deploy

## Gate (must pass first)

!`cd "${CLAUDE_PROJECT_DIR}" && .venv/bin/python tools/deploy_gate.py || true`

If the gate output above says **DEPLOY REFUSED**: stop. Report the reasons exactly as printed and tell the user what to run (usually commit, then `/validate`). Do not try to satisfy the gate any other way: do not create or edit `verification/stamp.json`, do not run the checks yourself and call it validated.

If it says **DEPLOY ALLOWED**, run `.venv/bin/python tools/deploy_gate.py` once more yourself (the tree may have changed since this skill loaded) and continue only if it still allows.

## Deploy

No deploy target is configured yet: the service and its Vercel deployment arrive in milestone M6. Until then, report "gate passed, no deploy target configured (M6)" and stop.
