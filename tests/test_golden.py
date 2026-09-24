import json

import pytest

from engine.conventions.packs import get_pack
from engine.instruments.equity_option.pricer import price
from engine.market.snapshot import load_snapshot

from conftest import GOLDEN, SNAPSHOT_IDS, load_cases

REL_TOL = 1e-9
ABS_TOL = 1e-12
CASES = load_cases()


def _expected(snapshot_id):
    return json.loads((GOLDEN / "expected" / f"{snapshot_id}.json").read_text())


@pytest.mark.parametrize("snapshot_id", SNAPSHOT_IDS)
def test_expected_covers_every_case(snapshot_id):
    assert set(_expected(snapshot_id)["results"]) == {cid for cid, _ in CASES}


@pytest.mark.parametrize("snapshot_id", SNAPSHOT_IDS)
@pytest.mark.parametrize("case_id,spec", CASES, ids=[c[0] for c in CASES])
def test_golden(snapshot_id, case_id, spec):
    expected = _expected(snapshot_id)
    snap = load_snapshot(GOLDEN / "snapshots" / f"{snapshot_id}.json")
    result = price(spec, snap, get_pack(expected["pack"]))
    for field, want in expected["results"][case_id].items():
        assert getattr(result, field) == pytest.approx(want, rel=REL_TOL, abs=ABS_TOL), field
