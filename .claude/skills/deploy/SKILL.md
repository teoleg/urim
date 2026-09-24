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

## Deploy (Vercel, via CLI only)

GitHub auto-deploy is switched off in `vercel.json` (`git.deploymentEnabled: false`), because a push-triggered deploy would skip this gate. `/deploy` is the only deploy path, and the `deploy_guard` hook also blocks any deploying `vercel` command unless the gate passes.

1. Preconditions. If any is missing, stop and tell the user exactly what to set up; never work around it:
   - `VERCEL_TOKEN` is set in the environment (`test -n "$VERCEL_TOKEN" && echo set || echo missing`). Never print or echo the token itself.
   - The project is linked (`.vercel/project.json` exists, or the user gives the project name for `vercel link`).
   - `vercel.com` is reachable from this environment.
2. Deploy the validated commit:
   `npx --yes vercel deploy --prod --yes --token "$VERCEL_TOKEN" --env URIM_COMMIT="$(git rev-parse HEAD)"`
   Record the deployment URL it prints.
3. Smoke-test the deployment against the frozen golden values, including that it serves exactly the validated commit:
   `.venv/bin/python tools/smoke.py <deployment-url> --expect-commit "$(git rev-parse HEAD)"`
4. Report: URL, commit, gate result, smoke result line by line. If the smoke test fails, say so plainly and recommend rolling back in the Vercel dashboard (do not attempt automatic rollback).
