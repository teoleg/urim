"""Thummim's blinders: the verifier must not be able to read the builder's code."""
import json
import subprocess
import sys
from pathlib import Path

import pytest

HOOK = Path(__file__).resolve().parent.parent / ".claude" / "hooks" / "thummim_blinders.py"


def decision(project, tool, *flags, extra=None, **tool_input):
    proc = subprocess.run([sys.executable, str(HOOK), *flags], capture_output=True, text=True, timeout=30,
                          input=json.dumps({"hook_event_name": "PreToolUse", "tool_name": tool,
                                            "tool_input": tool_input, **(extra or {})}),
                          env={"CLAUDE_PROJECT_DIR": str(project), "PATH": ""})
    assert proc.returncode == 0, proc.stderr
    return json.loads(proc.stdout)["hookSpecificOutput"]["permissionDecision"] if proc.stdout.strip() else None


@pytest.mark.parametrize("tool,key,path", [
    ("Read", "file_path", "engine/instruments/equity_option/pricer.py"),
    ("Grep", "path", "engine"),
    ("Grep", "path", "."),
    ("Glob", "path", "engine/instruments"),
    ("Read", "file_path", ".git/HEAD"),
])
def test_reading_builder_code_denied(tmp_path, tool, key, path):
    assert decision(tmp_path, tool, **{key: str(tmp_path / path)}) == "deny"


def test_subagents_only_flag_ignores_main_conversation(tmp_path):
    pricer = str(tmp_path / "engine/instruments/equity_option/pricer.py")
    assert decision(tmp_path, "Read", "--subagents-only", file_path=pricer) is None
    assert decision(tmp_path, "Read", "--subagents-only", extra={"agent_id": "a1"}, file_path=pricer) == "deny"


def test_grep_without_path_searches_root_and_is_denied(tmp_path):
    assert decision(tmp_path, "Grep", pattern="NPV") == "deny"


@pytest.mark.parametrize("tool,key,path", [
    ("Read", "file_path", "tests/golden/cases.json"),
    ("Read", "file_path", "tests/golden/snapshots/SYN-EQ-2026-09-24.json"),
    ("Grep", "path", "verification"),
    ("Read", "file_path", "verification/report.md"),
])
def test_reading_inputs_allowed(tmp_path, tool, key, path):
    assert decision(tmp_path, tool, **{key: str(tmp_path / path)}) is None


@pytest.mark.parametrize("path,expected", [
    ("verification/reference/black_scholes.py", None),
    ("tests/test_verification.py", None),
    ("engine/instruments/equity_option/pricer.py", "deny"),
    ("tests/golden/cases.json", "deny"),
    ("CLAUDE.md", "deny"),
])
def test_write_scope(tmp_path, path, expected):
    assert decision(tmp_path, "Write", file_path=str(tmp_path / path)) == expected


@pytest.mark.parametrize("command", [
    ".venv/bin/python -m engine.cli price --snapshot tests/golden/snapshots/S.json --type call "
    "--strike 100 --expiry 2027-09-24 --pack EQ-EURO-US-v1",
    ".venv/bin/python verification/verify.py",
    ".venv/bin/python verification/verify.py 2>&1 | tail -20",
    ".venv/bin/python -m pytest -q tests/test_verification.py",
    "mkdir -p verification/reference",
    "cat tests/golden/cases.json",
])
def test_bash_allowed(tmp_path, command):
    assert decision(tmp_path, "Bash", command=command) is None


@pytest.mark.parametrize("command", [
    "cat engine/instruments/equity_option/pricer.py",
    "git log -p",
    "git show HEAD",
    "grep -r NPV .",
    "python -c 'import engine'",
    ".venv/bin/python -m pytest -q",
    "find . -name '*.py'",
    "cat $(ls -d eng*)/cli.py",
    "cat tests/*/*.py",
    "cat tests/golden/cases.json > verification/x.json",
    "sed -n 1p verification/x.py",
])
def test_bash_denied(tmp_path, command):
    assert decision(tmp_path, "Bash", command=command) == "deny"
