"""deploy_guard hook: Vercel commands that can deploy must pass the deploy gate."""
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
HOOK = ROOT / ".claude" / "hooks" / "deploy_guard.py"
sys.path.insert(0, str(HOOK.parent))
from deploy_guard import vercel_may_deploy  # noqa: E402


@pytest.mark.parametrize("command", [
    "vercel",
    "vercel --prod",
    "vercel deploy --prod --yes",
    "npx --yes vercel deploy --prod",
    "npx vercel@latest --prod",
    "cd x && vercel promote https://a.vercel.app",
    "vercel --token abc deploy",
])
def test_deploying_commands_detected(command):
    assert vercel_may_deploy(command)


@pytest.mark.parametrize("command", [
    "vercel whoami",
    "npx vercel ls",
    "vercel env ls",
    "vercel --version",
    "cat vercel.json",
    "grep vercel README.md",
    "git add vercel.json",
    "pytest -q",
])
def test_safe_commands_pass(command):
    assert not vercel_may_deploy(command)


def run_hook(project, command):
    proc = subprocess.run([sys.executable, str(HOOK)], capture_output=True, text=True, timeout=60,
                          input=json.dumps({"tool_name": "Bash", "tool_input": {"command": command}}),
                          env={**os.environ, "CLAUDE_PROJECT_DIR": str(project)})
    return json.loads(proc.stdout)["hookSpecificOutput"] if proc.stdout.strip() else None


def test_deploy_denied_when_gate_refuses(tmp_path):
    (tmp_path / "tools").mkdir()
    (tmp_path / "tools" / "deploy_gate.py").write_text("print('DEPLOY REFUSED\\n- no stamp'); raise SystemExit(1)\n")
    out = run_hook(tmp_path, "vercel deploy --prod")
    assert out["permissionDecision"] == "deny" and "no stamp" in out["permissionDecisionReason"]


def test_deploy_allowed_when_gate_passes(tmp_path):
    (tmp_path / "tools").mkdir()
    (tmp_path / "tools" / "deploy_gate.py").write_text("print('DEPLOY ALLOWED')\n")
    assert run_hook(tmp_path, "vercel deploy --prod") is None


def test_safe_command_does_not_run_gate(tmp_path):
    assert run_hook(tmp_path, "vercel whoami") is None  # no gate script exists; must not be needed
