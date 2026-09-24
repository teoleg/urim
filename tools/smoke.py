"""Smoke-test a running Urim service (local or deployed) against the frozen golden values.

Usage: python tools/smoke.py BASE_URL [--expect-commit SHA]
Exit 0 if every check passes, 1 otherwise.
"""
from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path

import httpx
from mcp import Client

ROOT = Path(__file__).resolve().parent.parent
SNAPSHOT_ID = "SYN-EQ-2026-09-24"
CASE = "call-atm-1y"
REQ = {"snapshot_id": SNAPSHOT_ID, "option_type": "call", "strike": 100.0, "expiry": "2027-09-24",
       "pack": "EQ-EURO-US-v1"}
REL_TOL = 1e-9


def expected_price() -> float:
    doc = json.loads((ROOT / "tests" / "golden" / "expected" / f"{SNAPSHOT_ID}.json").read_text())
    return doc["results"][CASE]["price"]


def close(a: float, b: float) -> bool:
    return abs(a - b) <= REL_TOL * max(abs(b), 1e-12)


async def mcp_price(base: str) -> float:
    async with Client(f"{base}/mcp") as c:
        result = await c.call_tool("price_european_option", REQ)
        if result.is_error:
            raise RuntimeError(result.content[0].text)
        data = result.structured_content or json.loads(result.content[0].text)
        return data.get("result", data)["price"]


def main(argv: list[str]) -> int:
    if not argv or argv[0].startswith("-"):
        print(__doc__, file=sys.stderr)
        return 2
    base = argv[0].rstrip("/")
    expect_commit = argv[argv.index("--expect-commit") + 1] if "--expect-commit" in argv else None
    want = expected_price()
    checks: list[tuple[str, bool, str]] = []

    def check(name, fn):
        try:
            ok, detail = fn()
        except Exception as exc:  # a smoke test reports, it doesn't crash
            ok, detail = False, repr(exc)
        checks.append((name, ok, detail))

    with httpx.Client(timeout=60) as http:
        def health():
            body = http.get(f"{base}/health").json()
            ok = body.get("status") == "ok" and (expect_commit is None or body.get("commit") == expect_commit)
            return ok, f"commit={body.get('commit')}" + (f" expected={expect_commit}" if expect_commit else "")

        def rest_price():
            body = http.post(f"{base}/price", json=REQ).json()
            ok = close(body["price"], want) and body["snapshot_id"] == SNAPSHOT_ID and body.get("conventions")
            return bool(ok), f"price={body['price']!r} golden={want!r}"

        def refuses_without_pack():
            r = http.post(f"{base}/price", json={k: v for k, v in REQ.items() if k != "pack"})
            return r.status_code == 422, f"status={r.status_code}"

        check("health", health)
        check("rest_price_matches_golden", rest_price)
        check("rest_refuses_without_pack", refuses_without_pack)

    def mcp_check():
        got = asyncio.run(mcp_price(base))
        return close(got, want), f"price={got!r} golden={want!r}"

    check("mcp_price_matches_golden", mcp_check)

    for name, ok, detail in checks:
        print(f"{'PASS' if ok else 'FAIL'}  {name}: {detail}")
    passed = all(ok for _, ok, _ in checks)
    print(f"SMOKE: {'PASS' if passed else 'FAIL'} ({base})")
    return 0 if passed else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
