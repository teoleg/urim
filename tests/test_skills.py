"""Skills are instructions, but their scripts and structure can still be tested."""
import json
import re
import subprocess
import sys
from pathlib import Path

import pytest
import yaml

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


def frontmatter(path):
    """Parse YAML frontmatter. Claude Code silently drops ALL fields when the YAML is invalid."""
    text = path.read_text()
    assert text.startswith("---\n"), "frontmatter must start on line 1"
    return yaml.safe_load(text.split("---\n")[1])


@pytest.mark.parametrize("skill", ["market-snapshot", "conventions", "add-instrument"])
def test_skill_frontmatter_parses(skill):
    front = frontmatter(SKILLS / skill / "SKILL.md")
    assert front["name"] == skill
    assert len(front["description"]) >= 40
    assert len(front["description"] + front.get("when_to_use", "")) <= 1536  # listing cap


def test_conventions_skill_scoping_fields():
    front = frontmatter(SKILLS / "conventions" / "SKILL.md")
    # no `paths`: the 2026-09-24 acceptance run showed it hid the skill from pricing requests
    assert "paths" not in front
    assert "list_packs.py" in front["allowed-tools"]


def test_thummim_agent_frontmatter_parses():
    front = frontmatter(ROOT / ".claude" / "agents" / "thummim.md")
    assert front["name"] == "thummim" and front["omitClaudeMd"] is True
    command = front["hooks"]["PreToolUse"][0]["hooks"][0]["command"]
    assert "thummim_blinders.py" in command


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
