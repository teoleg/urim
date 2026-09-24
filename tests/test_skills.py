"""Skills are instructions, but their scripts and structure can still be tested."""
import json
import re
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
SKILLS = ROOT / ".claude" / "skills"
GOOD = {
    "snapshot_id": "SYN-EQ-2026-09-24", "as_of": "2026-09-24", "underlying": "SYNTH", "spot": 100.0,
    "rate": 0.04, "div_yield": 0.0, "vol": 0.25, "synthetic": True, "source": "Synthetic test data.",
}


def validate(*paths):
    return subprocess.run([sys.executable, str(SKILLS / "market-snapshot" / "validate.py"), *map(str, paths)],
                          capture_output=True, text=True, timeout=60)


def write(tmp_path, name, data):
    p = tmp_path / f"{name}.json"
    p.write_text(json.dumps(data))
    return p


@pytest.mark.parametrize("skill", ["market-snapshot", "conventions", "add-instrument"])
def test_skill_has_frontmatter_with_description(skill):
    text = (SKILLS / skill / "SKILL.md").read_text()
    assert text.startswith("---\n"), "frontmatter must start on line 1"
    front = text.split("---\n")[1]
    assert re.search(r"^description: .{40,}", front, re.M)
    assert re.search(rf"^name: {skill}$", front, re.M)


@pytest.mark.parametrize("skill,files", [
    ("market-snapshot", ["template.json", "validate.py"]),
    ("add-instrument", ["checklist.md"]),
])
def test_linked_supporting_files_exist(skill, files):
    for f in files:
        assert (SKILLS / skill / f).exists()


def test_validator_accepts_golden_snapshots():
    proc = validate(*sorted((ROOT / "tests" / "golden" / "snapshots").glob("*.json")))
    assert proc.returncode == 0, proc.stdout


def test_validator_accepts_good_snapshot(tmp_path):
    assert validate(write(tmp_path, GOOD["snapshot_id"], GOOD)).returncode == 0


@pytest.mark.parametrize("change,message", [
    ({"vol": 25.0}, "percentages"),
    ({"source": "made up"}, "say 'synthetic'"),
    ({"snapshot_id": "MY-SNAP"}, "SYN-"),
    ({"as_of": "2026-09-25"}, "does not match as_of"),
    ({"synthetic": False, "source": "web"}, "public source"),
])
def test_validator_rejects(tmp_path, change, message):
    data = {**GOOD, **change}
    proc = validate(write(tmp_path, data["snapshot_id"], data))
    assert proc.returncode == 1 and message in proc.stdout, proc.stdout


def test_validator_rejects_id_file_mismatch(tmp_path):
    proc = validate(write(tmp_path, "OTHER-NAME", GOOD))
    assert proc.returncode == 1 and "file name" in proc.stdout


def test_list_packs_script_prints_registered_packs():
    proc = subprocess.run([sys.executable, str(SKILLS / "conventions" / "list_packs.py")],
                          capture_output=True, text=True, timeout=60)
    assert proc.returncode == 0
    assert json.loads(proc.stdout)["EQ-EURO-US-v1"]["day_count"] == "ACT/365F"
