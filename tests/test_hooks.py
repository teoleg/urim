"""Hooks are code too: feed them the JSON Claude Code sends and check the decision."""
import json
import subprocess
import sys
from pathlib import Path

import pytest

HOOKS = Path(__file__).resolve().parent.parent / ".claude" / "hooks"


def run_hook(name, payload, project):
    proc = subprocess.run([sys.executable, str(HOOKS / name)], input=json.dumps(payload),
                          capture_output=True, text=True, env={"CLAUDE_PROJECT_DIR": str(project), "PATH": ""},
                          timeout=60)
    assert proc.returncode == 0, proc.stderr
    return json.loads(proc.stdout) if proc.stdout.strip() else None


def pre(project, tool, **tool_input):
    out = run_hook("protect_paths.py", {"hook_event_name": "PreToolUse", "tool_name": tool,
                                        "tool_input": tool_input}, project)
    return out["hookSpecificOutput"]["permissionDecision"] if out else None


# --- protect_paths: file tools ---------------------------------------------------------

@pytest.mark.parametrize("tool", ["Edit", "Write"])
def test_golden_expected_edit_denied(tmp_path, tool):
    assert pre(tmp_path, tool, file_path=str(tmp_path / "tests/golden/expected/X.json")) == "deny"


def test_relative_spelling_is_resolved(tmp_path):
    path = str(tmp_path / "tests/golden/snapshots/../expected/X.json")
    assert pre(tmp_path, "Edit", file_path=path) == "deny"


def test_ordinary_file_untouched(tmp_path):
    assert pre(tmp_path, "Edit", file_path=str(tmp_path / "engine/cli.py")) is None


def test_golden_snapshot_and_cases_not_frozen(tmp_path):
    assert pre(tmp_path, "Write", file_path=str(tmp_path / "tests/golden/snapshots/NEW.json")) is None


VALIDATED = "engine/instruments/equity_option/validated/pricer.py"


def test_validated_denied_without_adr(tmp_path):
    assert pre(tmp_path, "Edit", file_path=str(tmp_path / VALIDATED)) == "deny"


@pytest.mark.parametrize("status,expected", [("Accepted", None), ("Proposed", "deny")])
def test_validated_needs_accepted_adr(tmp_path, status, expected):
    adr = tmp_path / "docs/adr/0001-change.md"
    adr.parent.mkdir(parents=True)
    adr.write_text(f"# 0001\nStatus: {status}\nPaths: {VALIDATED}\n")
    assert pre(tmp_path, "Edit", file_path=str(tmp_path / VALIDATED)) == expected


def test_adr_for_other_path_does_not_count(tmp_path):
    adr = tmp_path / "docs/adr/0001-change.md"
    adr.parent.mkdir(parents=True)
    adr.write_text("Status: Accepted\nPaths: engine/other/validated/x.py\n")
    assert pre(tmp_path, "Edit", file_path=str(tmp_path / VALIDATED)) == "deny"


# --- protect_paths: Bash (best effort) --------------------------------------------------

@pytest.mark.parametrize("command", [
    "cat tests/golden/expected/X.json",
    "git diff tests/golden/expected/",
    "grep price tests/golden/expected/X.json | head -3",
    "python -m pytest -q 2>&1 | tail -3",
    "ls engine/instruments/equity_option/validated/",
])
def test_bash_read_only_allowed(tmp_path, command):
    assert pre(tmp_path, "Bash", command=command) is None


@pytest.mark.parametrize("command", [
    "rm tests/golden/expected/X.json",
    "sed -i s/1/2/ tests/golden/expected/X.json",
    "echo {} > tests/golden/expected/X.json",
    "cat a.json | tee tests/golden/expected/X.json",
    "cp new.json tests/golden/expected/X.json",
    "git checkout -- tests/golden/expected/X.json",
    "ls && mv x.py engine/a/validated/y.py",
])
def test_bash_writes_denied(tmp_path, command):
    assert pre(tmp_path, "Bash", command=command) == "deny"


def test_bash_quoted_angle_bracket_is_not_a_redirect(tmp_path):
    assert pre(tmp_path, "Bash", command='grep "a>b" tests/golden/expected/X.json') is None


def test_bash_discarding_output_is_not_a_write(tmp_path):
    """False positive found by the 2026-09-24 acceptance run."""
    assert pre(tmp_path, "Bash", command="ls tests/golden/expected 2>/dev/null") is None
    assert pre(tmp_path, "Bash", command="ls tests/golden/expected > /dev/null") is None
    assert pre(tmp_path, "Bash", command="ls tests/golden/expected > out.txt") == "deny"
    assert pre(tmp_path, "Bash", command="cat tests/golden/expected/X.json # By: A <a@b.com>") is None


def test_hook_fails_closed_on_bad_input(tmp_path):
    proc = subprocess.run([sys.executable, str(HOOKS / "protect_paths.py")], input="not json",
                          capture_output=True, text=True, env={"CLAUDE_PROJECT_DIR": str(tmp_path)})
    assert json.loads(proc.stdout)["hookSpecificOutput"]["permissionDecision"] == "deny"


# --- test_on_edit ------------------------------------------------------------------------

def post(project, relpath):
    return run_hook("test_on_edit.py", {"hook_event_name": "PostToolUse", "tool_name": "Edit",
                                        "tool_input": {"file_path": str(project / relpath)}}, project)


def make_project(tmp_path, passing):
    (tmp_path / "tests").mkdir()
    (tmp_path / "tests" / "test_x.py").write_text(f"def test_x():\n    assert {passing}\n")
    return tmp_path


def test_on_edit_passing_is_silent(tmp_path):
    assert post(make_project(tmp_path, True), "engine/a.py") is None


def test_on_edit_failure_blocks_with_output(tmp_path):
    out = post(make_project(tmp_path, False), "engine/a.py")
    assert out["decision"] == "block"
    assert "engine/a.py" in out["reason"] and "test_x" in out["reason"]


def test_on_edit_ignores_unwatched_files(tmp_path):
    assert post(make_project(tmp_path, False), "README.md") is None
