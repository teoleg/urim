import warnings
from dataclasses import replace

import pytest

from engine.conventions.packs import get_pack
from engine.instruments.equity_option.invariants import BLOCKING, WARNING, check_put_call_parity, run_checks
from engine.instruments.equity_option.pricer import price
from engine.market.snapshot import load_snapshot

from conftest import GOLDEN, SNAPSHOT_IDS, load_cases

PACK = get_pack("EQ-EURO-US-v1")
CASES = load_cases()


@pytest.mark.parametrize("snapshot_id", SNAPSHOT_IDS)
@pytest.mark.parametrize("case_id,spec", CASES, ids=[c[0] for c in CASES])
def test_invariants(snapshot_id, case_id, spec):
    snap = load_snapshot(GOLDEN / "snapshots" / f"{snapshot_id}.json")
    checks = run_checks(spec, snap, PACK)
    blocking_failures = [c for c in checks if c.severity == BLOCKING and c.failed]
    assert not blocking_failures, blocking_failures
    for c in checks:
        if c.severity == WARNING and c.failed:
            warnings.warn(f"{snapshot_id}/{case_id} {c.name}: {c.detail}")


def test_expiry_monotonicity_actually_runs_on_q0_calls():
    snap = load_snapshot(GOLDEN / "snapshots" / f"{SNAPSHOT_IDS[1]}.json")
    ran = [c for _, spec in CASES if spec.option_type == "call"
           for c in run_checks(spec, snap, PACK) if c.name == "call_monotone_in_expiry"]
    assert ran and all(c.status == "pass" for c in ran)


def test_parity_check_can_fail():
    """A check that can never fail proves nothing: feed it a deliberately wrong price."""
    snap = load_snapshot(GOLDEN / "snapshots" / f"{SNAPSHOT_IDS[0]}.json")
    _, spec = CASES[0]
    wrong = replace(price(spec, snap, PACK), price=price(spec, snap, PACK).price + 0.01)
    assert check_put_call_parity(spec, snap, PACK, wrong).failed


def test_european_put_below_intrinsic_is_allowed():
    """Deep ITM European put may be worth less than K - S; the bound is the discounted one."""
    snap = load_snapshot(GOLDEN / "snapshots" / f"{SNAPSHOT_IDS[0]}.json")
    spec = dict(CASES)["put-deep-itm-5y"]
    p = price(spec, snap, PACK).price
    assert p < spec.strike - snap.spot
    assert not [c for c in run_checks(spec, snap, PACK) if c.name == "no_arbitrage_bounds" and c.failed]
