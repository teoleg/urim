#!/usr/bin/env python3
"""PreToolUse hook (Bash): any Vercel command that can deploy must pass tools/deploy_gate.py first.

The /deploy skill runs the gate too; this hook makes the rule hold even if Claude skips /deploy.
Read-only Vercel subcommands (whoami, ls, inspect, logs, ...) pass through. Fails closed.
"""
from __future__ import annotations

import json
import os
import re
import shlex
import subprocess
import sys
from pathlib import Path

SAFE_SUBCOMMANDS = {"whoami", "ls", "list", "inspect", "logs", "help", "login", "logout", "link", "pull",
                    "project", "projects", "teams", "switch", "domains", "dns", "certs", "env", "--version",
                    "-v", "--help", "-h"}


LAUNCHERS = {"npx", "bunx", "pnpx", "exec", "dlx", "--yes", "-y", "env", "command"}


def decide(decision: str, reason: str) -> None:
    print(json.dumps({"hookSpecificOutput": {
        "hookEventName": "PreToolUse", "permissionDecision": decision, "permissionDecisionReason": reason}}))


def vercel_may_deploy(command: str) -> bool:
    for segment in re.split(r"&&|\|\||;|\||\n", command):
        try:
            words = shlex.split(segment)
        except ValueError:
            return "vercel" in segment  # can't parse: assume the worst
        for i, w in enumerate(words):
            is_command = i == 0 or words[i - 1] in LAUNCHERS
            if is_command and (w == "vercel" or w.startswith("vercel@")):
                args = [a for a in words[i + 1:] if not a.startswith("--token") and not a.startswith("--scope")]
                first = next((a for a in args if not a.startswith("-") or a in SAFE_SUBCOMMANDS), None)
                if first is None or first not in SAFE_SUBCOMMANDS:
                    return True  # bare `vercel`, `vercel deploy`, `vercel --prod`, `vercel promote`, ...
    return False


def main() -> int:
    data = json.load(sys.stdin)
    command = (data.get("tool_input") or {}).get("command", "")
    if not vercel_may_deploy(command):
        return 0
    root = Path(os.environ.get("CLAUDE_PROJECT_DIR") or data.get("cwd") or ".")
    python = root / ".venv" / "bin" / "python"
    gate = subprocess.run([str(python) if python.exists() else sys.executable, "tools/deploy_gate.py"],
                          cwd=root, capture_output=True, text=True, timeout=60)
    if gate.returncode != 0:
        decide("deny", "Deploy blocked by tools/deploy_gate.py:\n" + gate.stdout.strip()
               + "\nCommit, run /validate, then deploy via /deploy.")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as exc:  # fail closed
        decide("deny", f"deploy_guard hook error, denying to be safe: {exc!r}")
        sys.exit(0)
