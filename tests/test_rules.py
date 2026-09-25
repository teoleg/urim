"""Path-scoped rules: valid frontmatter, and every pattern matches a real file (a typo would never load)."""
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parent.parent
RULES = sorted((ROOT / ".claude" / "rules").glob("*.md"))


def frontmatter(path):
    text = path.read_text()
    assert text.startswith("---\n"), "frontmatter must start on line 1"
    return yaml.safe_load(text.split("---\n")[1])


def test_rules_exist():
    assert {p.name for p in RULES} == {"engine.md", "verification.md", "service.md"}


@pytest.mark.parametrize("rule", RULES, ids=[p.name for p in RULES])
def test_every_path_pattern_matches_something(rule):
    patterns = frontmatter(rule)["paths"]
    assert patterns
    for pattern in patterns:
        assert any(ROOT.glob(pattern)), f"{rule.name}: {pattern!r} matches no file"


def test_claude_md_points_at_every_rule():
    text = (ROOT / "CLAUDE.md").read_text()
    for rule in RULES:
        assert f"`{rule.name}`" in text
