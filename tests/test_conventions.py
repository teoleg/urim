from datetime import date

import pytest

from engine.cli import main
from engine.conventions.packs import ConventionError, get_pack
from engine.instruments.equity_option.pricer import OptionSpec, price
from engine.market.snapshot import load_snapshot

PACK = "EQ-EURO-US-v1"


@pytest.mark.parametrize("name", [None, ""])
def test_no_pack_refused(name):
    with pytest.raises(ConventionError, match="no convention pack"):
        get_pack(name)


def test_unknown_pack_refused():
    with pytest.raises(ConventionError, match="unknown"):
        get_pack("EQ-MADE-UP")


def test_price_requires_pack(golden_snapshot_path):
    with pytest.raises(ConventionError):
        price(OptionSpec("call", 100, date(2027, 9, 24)), load_snapshot(golden_snapshot_path), None)


def test_result_discloses_conventions_and_snapshot(golden_snapshot_path):
    snap = load_snapshot(golden_snapshot_path)
    result = price(OptionSpec("call", 100, date(2027, 9, 24)), snap, get_pack(PACK))
    assert result.conventions == get_pack(PACK).to_dict()
    assert result.snapshot_id == snap.snapshot_id
    assert result.as_of == "2026-09-24"
    assert result.synthetic_data is True


def test_non_business_day_expiry_refused(golden_snapshot_path):
    # 2026-12-26 is a Saturday
    with pytest.raises(ConventionError, match="not a business day"):
        price(OptionSpec("call", 100, date(2026, 12, 26)), load_snapshot(golden_snapshot_path), get_pack(PACK))


def test_expiry_before_as_of_refused(golden_snapshot_path):
    with pytest.raises(ValueError, match="after snapshot"):
        price(OptionSpec("call", 100, date(2026, 9, 24)), load_snapshot(golden_snapshot_path), get_pack(PACK))


def test_cli_without_pack_fails(golden_snapshot_path):
    with pytest.raises(SystemExit):
        main(["price", "--snapshot", str(golden_snapshot_path), "--type", "call", "--strike", "100",
              "--expiry", "2027-09-24"])


def test_cli_prints_result(golden_snapshot_path, capsys):
    rc = main(["price", "--snapshot", str(golden_snapshot_path), "--type", "put", "--strike", "100",
               "--expiry", "2027-09-24", "--pack", PACK])
    assert rc == 0
    assert '"snapshot_id": "SYN-EQ-2026-09-24"' in capsys.readouterr().out
