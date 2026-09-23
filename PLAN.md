# PLAN.md — Quant Agent Kit (working name: **Urim** — TBD, see Open Decisions)

Seed brief carried over from a design chat (2026-09-23). Read fully before doing anything.

## 0. Instructions for Claude Code — first session

1. **Do not scaffold yet.** Interview me first. I want two-way dialog on complex problems: ask questions, challenge assumptions, help me sharpen my own questions. No "got it" followed by generated output.
2. Walk through **§9 Open Decisions** with me, one at a time. Record answers in this file.
3. Then: derive `CLAUDE.md` from §6–§7, create the GitHub repo with `gh`, commit `PLAN.md` + `CLAUDE.md`, push.
4. Work milestone by milestone (§8). Stop at the end of each milestone for review. Never start the next one unasked.
5. Before building any Claude Code component (plugin, skill, hook, subagent, command, MCP), check the current Claude Code docs for the exact format — do not rely on memory.

## 1. Dual goal

- **Learn Claude Code in depth** — build and *use* every component: CLAUDE.md, settings/permissions, skills, slash commands, subagents, hooks, MCP servers, plugins + marketplace, headless / Agent SDK / GitHub Actions.
- **Ship a product** — a Claude Code plugin that lets *other* developers build, verify and run a financial pricing service.

Tension: learning wants breadth, product wants a narrow MVP. Resolution: **one thin vertical slice, end to end, using every component**, before adding a second instrument.

## 2. Product thesis

The product is the **plugin** (skills + workflows), not the pricing library. QuantLib is raw material.

Market scan (2026-09) — nothing joins these two halves:
- **Claude Code finance plugins** — analyst workflows (Anthropic `financial-services`: /dcf, /comps, …; LSEG plugin tied to LSEG licensing; community skill packs with reference scripts). None stand up a running service.
- **Service-grade engines** — ORE (on QuantLib, BSD, batch/XML-driven, not agent-native); one-off QuantLib+FastAPI tutorial repos.
- Adjacent: LSEG MCP (licensed analytics), SSCMFI (bond math as REST + C lib + MCP, same "no hallucinated math" pitch), `fixed-income-mcp` (self-checking bond analytics — note the idea).

Honest risks:
1. **Copyability** — a plugin is instructions + code. What is paid? (hosted runtime, validated model packs, certified adapters, support)
2. **Trust** — regulated users need model-validation evidence. The **verification layer may be the real product**.
3. **Buyer** — fintechs without quants (want it, pay little) vs. bank desks (pay, but have Numerix/ORE/in-house).

## 3. Target user journey (draft — refine in session 1)

> Developer installs the plugin, runs `/new-pricing-service irs`, and ~20 min later has a tested, deployed service: curve build, IRS pricing, DV01, REST + MCP endpoints, and a verifier that blocks wrong numbers from shipping.

## 4. Architecture (draft)

```
plugin/                      # the product
  .claude-plugin/plugin.json
  skills/                    # bootstrap-curve, add-instrument, conventions, deploy-vercel
  commands/                  # /new-pricing-service, /validate, /deploy
  agents/                    # builder, verifier (independent)
  hooks/                     # test-on-edit, protect-validated-models
  .mcp.json
engine/                      # Python + QuantLib — what the plugin generates/extends
  curves/ instruments/ risk/ conventions/
service/                     # FastAPI + MCP endpoint over engine
tests/golden/                # frozen market snapshots + expected results
```

Runtime target: **Vercel** (Python functions, deploy via GitHub integration).
- Fits: QuantLib size is fine (Python bundle limit 500MB; large functions beta up to 5GB).
- Does not fit: state. Stateless serverless → curves rebuilt per cold start, no in-memory market state, long jobs need Vercel Workflows. OK for v0 demo; not for stateful/low-latency (revisit later — this is where my own infra could differentiate).

## 5. Vertical slice v0 — vanilla IRS

Quotes in (deposits/futures/swaps, dated snapshot) → curve bootstrap → IRS NPV + par rate → DV01 → REST + MCP → independent verification.

Market data: **synthetic or clearly public** snapshots only. No licensed vendor data in the repo.

## 6. Verification design (the differentiator)

Verifier subagent (**Thummim**) — independent: does not see the builder's reasoning, reprices with a different method where possible.

Invariants every result must satisfy:
- Bootstrapped curve reprices every input instrument within tolerance.
- Discount factors in (0, 1], monotonic non-increasing (flag, don't assume, in negative-rate regimes).
- Swap priced at its par rate has NPV ≈ 0.
- DV01: analytic/engine value vs. bump-and-reprice agree within tolerance.
- Golden tests: frozen snapshot → frozen expected outputs; any diff fails.
- Every result carries curve snapshot ID + as-of date + conventions used.

## 7. Guardrails (plugin must refuse)

- Price without a dated, identified curve snapshot.
- Deploy without golden tests + verifier passing.
- Edit validated models (`engine/**/validated/`) without an explicit ADR.
- Silently assume conventions (day count, calendar, roll, payment freq) — must state or ask.
- Commit secrets or licensed data.

## 8. Milestones = Claude Code curriculum

| # | Deliverable | Claude Code components learned |
|---|---|---|
| M0 | Repo, PLAN.md, CLAUDE.md, pushed | CLAUDE.md, `gh`, settings/permissions |
| M1 | Engine slice + golden tests | plan mode, iterative build, test loop |
| M2 | Test-on-edit + protect-validated hooks | **hooks** (PostToolUse, PreToolUse) |
| M3 | Thummim verifier | **subagents** |
| M4 | Domain skills (curve, instrument, conventions) | **skills** |
| M5 | /new-pricing-service, /validate, /deploy | **slash commands** |
| M6 | FastAPI + MCP endpoint, Vercel deploy via GitHub | **MCP server**, deploy workflow |
| M7 | Package as plugin + local marketplace; install into a clean repo and run §3 end to end | **plugins, marketplace** — the real acceptance test |
| M8 | PR validation agent in CI | **headless / Agent SDK / GitHub Actions** |

## 9. Open decisions (resolve in session 1)

1. **Name** — Urim (runtime/oracle; caveats: "oracle" reads crypto, Mormon association in US) vs. Bezalel (builder/kit) vs. family: Bezalel = kit, Urim = runtime, Thummim/Oholiab = verifier. Check GitHub/PyPI/trademark collisions.
2. **Persona** — fintech dev who doesn't know day counts, or quant who hates plumbing?
3. **First command** and exactly what exists when it finishes.
4. **Slice** — IRS confirmed, or munis/fixed income where I know the edge cases cold?
5. **Stack** — Python + QuantLib only for v0, or C++ path from the start?
6. **Open vs. closed** — open core + paid layer, or closed from day one? What is the paid part?
7. **Verification depth for v0** — which invariants are blocking vs. warnings?

## 10. Non-goals (v0)

- Multiple instruments, XVA, exotics.
- Live/licensed market data feeds.
- Stateful or low-latency runtime.
- Monetization infrastructure.
