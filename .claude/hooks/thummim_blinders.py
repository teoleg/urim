#!/usr/bin/env python3
"""PreToolUse hook for the Thummim subagent (declared in .claude/agents/thummim.md frontmatter).

Keeps the verifier independent of the builder's code: Thummim may treat the engine only as a
black box through its CLI, and may write only under verification/ and tests/test_verification.py.

Allowlist, not blocklist. Best effort: a script Thummim writes could still open engine files,
so the agent prompt forbids that too. Fails closed.
"""
from __future__ import annotations

import json
import os
import re
import shlex
import sys
from pathlib import Path

WRITABLE = ("verification/", "tests/test_verification.py")
READ_BLOCKED = ("engine/", ".git/", ".claude/hooks/")
READ_ONLY_CMDS = {"ls", "cat", "head", "tail", "wc", "mkdir", "pwd"}
PYTHONS = {"python", "python3", ".venv/bin/python", ".venv/bin/python3"}


def decide(decision: str, reason: str) -> None:
    print(json.dumps({"hookSpecificOutput": {
        "hookEventName": "PreToolUse", "permissionDecision": decision, "permissionDecisionReason": reason}}))


def rel(path: str, root: Path) -> str | None:
    try:
        return Path(path.replace("\\", "/")).resolve().relative_to(root.resolve()).as_posix()
    except ValueError:
        return None  # outside the project


def blocked_read(relpath: str | None) -> bool:
    if relpath is None:
        return False
    return relpath in ("", ".") or any(relpath == p.rstrip("/") or relpath.startswith(p) for p in READ_BLOCKED)


def python_allowed(words: list[str]) -> bool:
    args = words[1:]
    if args[:2] == ["-m", "engine.cli"]:
        return True
    if args[:2] == ["-m", "pytest"]:
        # full-suite failures would print engine source in tracebacks: require the explicit file
        paths = [a for a in args[2:] if not a.startswith("-")]
        return bool(paths) and all(p.startswith("tests/test_verification") for p in paths)
    return bool(args) and args[0].startswith("verification/") and args[0].endswith(".py")


def check_bash(command: str) -> str | None:
    if re.search(r"[`$]|<\(|\bengine/", command):
        return "Thummim Bash may not use substitutions or mention engine/ paths."
    for segment in re.split(r"&&|\|\||;|\||\n", command):
        segment = re.sub(r"\s\d?>&\d\b|\s2>/dev/null\b", "", segment).strip()
        if not segment:
            continue
        try:
            words = shlex.split(segment)
        except ValueError:
            return f"Unparseable command segment: {segment!r}"
        if any(">" in w or "<" in w for w in words):
            return "Thummim Bash may not redirect; write files with the Write tool under verification/."
        head = words[0]
        if head in PYTHONS:
            if not python_allowed(words):
                return ("Thummim may run python only as: -m engine.cli ..., verification/*.py, "
                        "or -m pytest tests/test_verification.py.")
        elif head not in READ_ONLY_CMDS or any(w in (".", "..", "*") or "*" in w for w in words[1:]):
            return f"Command not on Thummim's allowlist: {segment!r}"
    return None


def main() -> int:
    data = json.load(sys.stdin)
    if "--subagents-only" in sys.argv and not data.get("agent_id"):
        return 0  # fallback wiring from settings.json: leave the main conversation alone
    root = Path(os.environ.get("CLAUDE_PROJECT_DIR") or data.get("cwd") or ".")
    tool, ti = data.get("tool_name"), data.get("tool_input") or {}

    reason = None
    if tool == "Bash":
        reason = check_bash(ti.get("command", ""))
    elif tool in ("Write", "Edit", "NotebookEdit"):
        r = rel(ti.get("file_path") or ti.get("notebook_path") or "", root)
        if r is None or not r.startswith(WRITABLE):
            reason = f"Thummim may write only under {', '.join(WRITABLE)}; got {r!r}."
    elif tool in ("Read", "Grep", "Glob"):
        target = ti.get("file_path") or ti.get("path") or str(root)
        if blocked_read(rel(target, root)):
            reason = ("Thummim is blind to the builder's code: no reading or searching engine/, .git/, "
                      ".claude/hooks/, or the whole repo root. Use the engine CLI as a black box.")
    if reason:
        decide("deny", reason)
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as exc:  # fail closed
        decide("deny", f"thummim_blinders hook error, denying to be safe: {exc!r}")
        sys.exit(0)
