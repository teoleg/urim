import pytest

from engine.market.snapshot import SnapshotError, load_snapshot, snapshot_from_dict

GOOD = {
    "snapshot_id": "T-1",
    "as_of": "2026-09-24",
    "underlying": "SYNTH",
    "spot": 100.0,
    "rate": 0.04,
    "div_yield": 0.01,
    "vol": 0.2,
    "synthetic": True,
    "source": "test",
}


def test_valid_snapshot_loads():
    snap = snapshot_from_dict(GOOD)
    assert snap.snapshot_id == "T-1"
    assert snap.as_of.isoformat() == "2026-09-24"


@pytest.mark.parametrize("field", ["snapshot_id", "as_of", "spot", "vol", "synthetic", "source"])
def test_missing_field_refused(field):
    data = {k: v for k, v in GOOD.items() if k != field}
    with pytest.raises(SnapshotError, match=field):
        snapshot_from_dict(data)


@pytest.mark.parametrize("field", ["snapshot_id", "as_of"])
def test_empty_identity_refused(field):
    with pytest.raises(SnapshotError, match=field):
        snapshot_from_dict({**GOOD, field: ""})


def test_bad_date_refused():
    with pytest.raises(SnapshotError, match="ISO date"):
        snapshot_from_dict({**GOOD, "as_of": "24/09/2026"})


@pytest.mark.parametrize("field", ["spot", "vol"])
@pytest.mark.parametrize("value", [0.0, -1.0])
def test_non_positive_refused(field, value):
    with pytest.raises(SnapshotError, match=field):
        snapshot_from_dict({**GOOD, field: value})


def test_golden_snapshot_is_synthetic(golden_snapshot_path):
    assert load_snapshot(golden_snapshot_path).synthetic is True
