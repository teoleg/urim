from pathlib import Path

import pytest

GOLDEN = Path(__file__).parent / "golden"
SNAPSHOT_ID = "SYN-EQ-2026-09-24"


@pytest.fixture
def golden_snapshot_path():
    return GOLDEN / "snapshots" / f"{SNAPSHOT_ID}.json"


SNAPSHOT_IDS = [SNAPSHOT_ID, f"{SNAPSHOT_ID}-Q0"]


def load_cases():
    import json
    from datetime import date

    from engine.instruments.equity_option.pricer import OptionSpec

    data = json.loads((GOLDEN / "cases.json").read_text())
    return [(c["id"], OptionSpec(c["option_type"], c["strike"], date.fromisoformat(c["expiry"]))) for c in data["cases"]]
