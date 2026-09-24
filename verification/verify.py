"""Thummim: independent verification of the Urim pricing engine.

The engine is treated as a black box, reached only through its CLI.
For every golden snapshot x case, the engine is priced and compared with the
independent reference in verification/reference/black_scholes.py.

Exit code 0 when all blocking checks pass, 1 otherwise.
Writes verification/report.json and verification/report.md.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from datetime import date, datetime, timezone

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)

from reference.black_scholes import bsm, year_fraction_act365f  # noqa: E402

PYTHON = os.path.join(ROOT, ".venv", "bin", "python")
SNAPSHOT_DIR = os.path.join(ROOT, "tests", "golden", "snapshots")
CASES_FILE = os.path.join(ROOT, "tests", "golden", "cases.json")
PACK = "EQ-EURO-US-v1"

# Tolerances (never loosen these to make a check pass).
PRICE_REL = 1e-8          # x max(1, spot)
TTE_ABS = 1e-12
PARITY_REL = 1e-8         # x spot
BOUNDS_EPS = 0.0          # bounds are checked exactly
GREEK_REL = 1e-6
GREEK_ABS_NEAR_ZERO = 1e-10
GREEKS = ("delta", "gamma", "vega", "theta", "rho")

# Interpretation of the engine's disclosed conventions and units.
EXPECTED_DAY_COUNT = "ACT/365F"
EXPECTED_UNITS_HINTS = {
    "vega": "per 1.00",
    "theta": "per year",
    "rho": "per 1.00",
}


def run_engine(snapshot_path: str, option_type: str, strike: float, expiry: str) -> dict:
    cmd = [
        PYTHON, "-m", "engine.cli", "price",
        "--snapshot", snapshot_path,
        "--type", option_type,
        "--strike", repr(float(strike)),
        "--expiry", expiry,
        "--pack", PACK,
    ]
    proc = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True)
    if proc.returncode != 0:
        raise RuntimeError(
            f"engine CLI failed (rc={proc.returncode}): {proc.stderr.strip() or proc.stdout.strip()}"
        )
    return json.loads(proc.stdout)


def check(name: str, passed: bool, blocking: bool, **details) -> dict:
    return {"check": name, "passed": bool(passed), "blocking": blocking, **details}


def greek_ok(engine_val: float, ref_val: float) -> tuple[bool, float, float]:
    abs_diff = abs(engine_val - ref_val)
    rel_diff = abs_diff / abs(ref_val) if ref_val != 0 else float("inf")
    if abs(ref_val) < GREEK_ABS_NEAR_ZERO / GREEK_REL:
        ok = abs_diff <= GREEK_ABS_NEAR_ZERO or rel_diff <= GREEK_REL
    else:
        ok = rel_diff <= GREEK_REL
    return ok, abs_diff, rel_diff


def verify_combo(snap: dict, snap_path: str, case: dict, engine_cache: dict) -> dict:
    spot, r, q, vol = snap["spot"], snap["rate"], snap["div_yield"], snap["vol"]
    as_of = date.fromisoformat(snap["as_of"])
    expiry = date.fromisoformat(case["expiry"])
    otype, strike = case["option_type"], float(case["strike"])

    def engine(option_type: str) -> dict:
        key = (snap_path, option_type, strike, case["expiry"])
        if key not in engine_cache:
            engine_cache[key] = run_engine(snap_path, option_type, strike, case["expiry"])
        return engine_cache[key]

    checks = []
    result = {
        "snapshot_id": snap["snapshot_id"],
        "case_id": case["id"],
        "option_type": otype,
        "strike": strike,
        "expiry": case["expiry"],
        "checks": checks,
    }

    try:
        eng = engine(otype)
        other = engine("put" if otype == "call" else "call")
    except Exception as exc:  # engine failure is a blocking failure
        checks.append(check("engine_call", False, True, error=str(exc)))
        return result

    result["engine"] = {k: eng.get(k) for k in ("price", *GREEKS, "time_to_expiry")}

    # --- metadata_present (blocking) ---
    missing = [k for k in ("snapshot_id", "as_of", "conventions", "engine") if not eng.get(k)]
    mismatches = []
    if eng.get("snapshot_id") != snap["snapshot_id"]:
        mismatches.append(f"snapshot_id engine={eng.get('snapshot_id')!r} file={snap['snapshot_id']!r}")
    if eng.get("as_of") != snap["as_of"]:
        mismatches.append(f"as_of engine={eng.get('as_of')!r} file={snap['as_of']!r}")
    conv = eng.get("conventions") or {}
    if isinstance(conv, dict) and conv.get("name") not in (None, PACK):
        mismatches.append(f"conventions.name engine={conv.get('name')!r} requested={PACK!r}")
    checks.append(check("metadata_present", not missing and not mismatches, True,
                        missing=missing, mismatches=mismatches))

    # Day count: use what the engine discloses; refuse to guess if it's something else.
    day_count = conv.get("day_count") if isinstance(conv, dict) else None
    if day_count != EXPECTED_DAY_COUNT:
        checks.append(check("day_count_supported", False, True,
                            error=f"engine discloses day_count={day_count!r}; reference implements "
                                  f"{EXPECTED_DAY_COUNT} only"))
        return result

    # Units: confirm the disclosed units match the reference's units.
    units = eng.get("units") or {}
    unit_issues = [
        f"{g}: engine says {units.get(g)!r}, reference expects '{hint}'"
        for g, hint in EXPECTED_UNITS_HINTS.items()
        if hint not in str(units.get(g, ""))
    ]

    t = year_fraction_act365f(as_of, expiry)
    ref = bsm(otype, spot, strike, t, r, q, vol)
    result["reference"] = {k: ref[k] for k in ("price", *GREEKS, "time_to_expiry")}

    # --- time_to_expiry_vs_reference (blocking) ---
    tte_diff = abs(float(eng["time_to_expiry"]) - t)
    checks.append(check("time_to_expiry_vs_reference", tte_diff <= TTE_ABS, True,
                        engine=eng["time_to_expiry"], reference=t, abs_diff=tte_diff, tol=TTE_ABS))

    # --- price_vs_reference (blocking) ---
    price_tol = PRICE_REL * max(1.0, spot)
    price_diff = abs(float(eng["price"]) - ref["price"])
    checks.append(check("price_vs_reference", price_diff <= price_tol, True,
                        engine=eng["price"], reference=ref["price"], abs_diff=price_diff, tol=price_tol))

    # --- put_call_parity (blocking), on engine prices, forward computed here ---
    call_px = float(eng["price"] if otype == "call" else other["price"])
    put_px = float(other["price"] if otype == "call" else eng["price"])
    parity_rhs = ref["forward_spot_pv"] - ref["strike_pv"]
    parity_diff = abs((call_px - put_px) - parity_rhs)
    parity_tol = PARITY_REL * spot
    checks.append(check("put_call_parity", parity_diff <= parity_tol, True,
                        call=call_px, put=put_px, c_minus_p=call_px - put_px,
                        s_eqT_minus_k_erT=parity_rhs, abs_diff=parity_diff, tol=parity_tol))

    # --- no_arbitrage_bounds (blocking), European discounted ---
    fs, pk = ref["forward_spot_pv"], ref["strike_pv"]
    px = float(eng["price"])
    if otype == "call":
        lo, hi = max(fs - pk, 0.0), fs
    else:
        lo, hi = max(pk - fs, 0.0), pk
    in_bounds = (lo - BOUNDS_EPS) <= px <= (hi + BOUNDS_EPS)
    checks.append(check("no_arbitrage_bounds", in_bounds, True, lower=lo, price=px, upper=hi))

    # --- greeks_vs_reference (warning) ---
    greek_rows = {}
    greeks_pass = True
    for g in GREEKS:
        ok, ad, rd = greek_ok(float(eng[g]), ref[g])
        greeks_pass &= ok
        greek_rows[g] = {"engine": eng[g], "reference": ref[g], "abs_diff": ad,
                         "rel_diff": rd, "passed": ok}
    checks.append(check("greeks_vs_reference", greeks_pass and not unit_issues, False,
                        greeks=greek_rows, unit_issues=unit_issues,
                        tol_rel=GREEK_REL, tol_abs_near_zero=GREEK_ABS_NEAR_ZERO))
    return result


def fmt(x) -> str:
    return f"{x:.6e}" if isinstance(x, float) else str(x)


def write_markdown(report: dict, path: str) -> None:
    lines = [
        "# Thummim verification report",
        "",
        f"- **Verdict:** {report['verdict']}",
        f"- Generated: {report['generated_at']}",
        f"- Convention pack: `{report['pack']}`",
        f"- Combinations checked: {report['combinations']} "
        f"(snapshots: {', '.join(report['snapshots'])})",
        f"- Blocking failures: {len(report['blocking_failures'])}; warnings: {len(report['warnings'])}",
        "",
        "## Interpretations",
        "",
        *[f"- {i}" for i in report["interpretations"]],
        "",
        "## Results",
        "",
        "| snapshot | case | price engine | price reference | |diff| | T | parity |diff| | bounds | metadata | greeks |",
        "|---|---|---|---|---|---|---|---|---|---|",
    ]
    for res in report["results"]:
        c = {x["check"]: x for x in res["checks"]}
        p = c.get("price_vs_reference", {})
        tt = c.get("time_to_expiry_vs_reference", {})
        pc = c.get("put_call_parity", {})

        def mark(name):
            x = c.get(name)
            return "n/a" if x is None else ("PASS" if x["passed"] else ("FAIL" if x["blocking"] else "WARN"))

        lines.append(
            f"| {res['snapshot_id']} | {res['case_id']} | {p.get('engine', 'n/a')} | "
            f"{p.get('reference', 'n/a')} | {fmt(p.get('abs_diff', 'n/a'))} | "
            f"{tt.get('engine', 'n/a')} ({mark('time_to_expiry_vs_reference')}) | "
            f"{fmt(pc.get('abs_diff', 'n/a'))} ({mark('put_call_parity')}) | "
            f"{mark('no_arbitrage_bounds')} | {mark('metadata_present')} | {mark('greeks_vs_reference')} |"
        )
    lines += ["", "## Blocking failures", ""]
    lines += [f"- {f}" for f in report["blocking_failures"]] or ["- none"]
    lines += ["", "## Warnings", ""]
    lines += [f"- {w}" for w in report["warnings"]] or ["- none"]
    lines += ["", "## Max Greek relative differences (engine vs reference)", ""]
    for g, v in report["max_greek_rel_diff"].items():
        lines.append(f"- {g}: {fmt(v)}")
    lines.append("")
    with open(path, "w") as fh:
        fh.write("\n".join(lines))


def main() -> int:
    with open(CASES_FILE) as fh:
        cases = json.load(fh)["cases"]
    snap_files = sorted(f for f in os.listdir(SNAPSHOT_DIR) if f.endswith(".json"))

    results, engine_cache, snapshot_ids = [], {}, []
    for fname in snap_files:
        snap_path = os.path.join(SNAPSHOT_DIR, fname)
        with open(snap_path) as fh:
            snap = json.load(fh)
        snapshot_ids.append(snap["snapshot_id"])
        for case in cases:
            results.append(verify_combo(snap, os.path.relpath(snap_path, ROOT), case, engine_cache))

    blocking_failures, warnings = [], []
    max_greek = {g: 0.0 for g in GREEKS}
    for res in results:
        tag = f"{res['snapshot_id']} / {res['case_id']}"
        for c in res["checks"]:
            if c["check"] == "greeks_vs_reference":
                for g, row in c["greeks"].items():
                    max_greek[g] = max(max_greek[g], row["rel_diff"])
            if c["passed"]:
                continue
            if c["check"] == "greeks_vs_reference":
                bad = {g: row for g, row in c["greeks"].items() if not row["passed"]}
                msg = "; ".join(
                    f"{g}: engine={row['engine']!r} ref={row['reference']!r} rel={row['rel_diff']:.3e}"
                    for g, row in bad.items()
                )
                if c["unit_issues"]:
                    msg += "; unit issues: " + "; ".join(c["unit_issues"])
                warnings.append(f"{tag}: greeks_vs_reference: {msg}")
            else:
                detail = {k: v for k, v in c.items() if k not in ("check", "passed", "blocking")}
                blocking_failures.append(f"{tag}: {c['check']}: {json.dumps(detail)}")

    verdict = "PASS" if not blocking_failures else "FAIL"
    report = {
        "verdict": verdict,
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "pack": PACK,
        "snapshots": snapshot_ids,
        "combinations": len(results),
        "engine_cli_calls": len(engine_cache),
        "tolerances": {
            "price_vs_reference": f"{PRICE_REL} * max(1, spot)",
            "time_to_expiry_vs_reference": TTE_ABS,
            "put_call_parity": f"{PARITY_REL} * spot",
            "no_arbitrage_bounds": "exact",
            "greeks_vs_reference": f"rel {GREEK_REL} (abs {GREEK_ABS_NEAR_ZERO} near zero)",
        },
        "interpretations": [
            "Day count taken from engine disclosure (ACT/365F): T = actual days(as_of, expiry) / 365. "
            "No calendar adjustment of expiry (cases' expiries are stated to be NYSE business days); "
            "no settlement lag (pack discloses 'none').",
            "Rate and dividend yield are continuously compounded and flat (per snapshot and disclosure).",
            "Vega per 1.00 of vol; rho per 1.00 of rate; theta = dV/dt per year of calendar time "
            "(i.e. -dV/dT), as disclosed in engine units.",
            "Put-call parity uses the engine price of the opposite option at the same strike/expiry, "
            "obtained by an extra CLI call where the case list has no pair.",
        ],
        "blocking_failures": blocking_failures,
        "warnings": warnings,
        "max_greek_rel_diff": max_greek,
        "results": results,
    }
    with open(os.path.join(HERE, "report.json"), "w") as fh:
        json.dump(report, fh, indent=2)
    write_markdown(report, os.path.join(HERE, "report.md"))

    print(f"VERDICT: {verdict}  ({len(results)} combinations, "
          f"{len(blocking_failures)} blocking failures, {len(warnings)} warnings)")
    for f in blocking_failures:
        print("FAIL:", f)
    for w in warnings:
        print("WARN:", w)
    print("max greek rel diff:", {g: f"{v:.2e}" for g, v in max_greek.items()})
    return 0 if verdict == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
