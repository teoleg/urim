"""Command skills: gate logic and invocation settings."""
import sys
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))
from deploy_gate import reasons_to_refuse  # noqa: E402

HEAD = "a" * 40
GOOD = {"commit": HEAD, "dirty": False, "tests_passed": True, "thummim_verify_passed": True,
        "created_at": "2026-09-24T00:00:00+00:00"}


def test_gate_allows_matching_clean_passing_stamp():
    assert reasons_to_refuse(GOOD, HEAD, dirty=False) == []


@pytest.mark.parametrize("stamp,dirty,fragment", [
    (None, False, "run /validate first"),
    ({**GOOD, "commit": "b" * 40}, False, "HEAD is"),
    (GOOD, True, "uncommitted"),
    ({**GOOD, "dirty": True}, False, "uncommitted"),
    ({**GOOD, "tests_passed": False}, False, "tests did not pass"),
    ({**GOOD, "thummim_verify_passed": False}, False, "Thummim"),
])
def test_gate_refuses(stamp, dirty, fragment):
    reasons = reasons_to_refuse(stamp, HEAD, dirty)
    assert reasons and any(fragment in r for r in reasons), reasons


def frontmatter(skill):
    return yaml.safe_load((ROOT / ".claude" / "skills" / skill / "SKILL.md").read_text().split("---\n")[1])


@pytest.mark.parametrize("skill,user_only", [("deploy", True), ("new-pricing-service", True), ("validate", False)])
def test_command_invocation_settings(skill, user_only):
    front = frontmatter(skill)
    assert front["name"] == skill and len(front["description"]) >= 40
    assert bool(front.get("disable-model-invocation")) is user_only


def test_validate_delegates_to_thummim_with_fixed_prompt():
    text = (ROOT / ".claude" / "skills" / "validate" / "SKILL.md").read_text()
    assert "subagent_type: thummim" in text and "> Re-verify the engine." in text
