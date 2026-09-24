#!/usr/bin/env python3
"""PreToolUse hook: protect frozen golden values and validated models.

- tests/golden/expected/**  : never edited by Claude's file tools. New snapshots are frozen
                              with tools/freeze_golden.py, which refuses to overwrite.
- engine/**/validated/**    : editable only when an accepted ADR in docs/adr/ names the path.
- Bash                      : best effort. A command segment that mentions a protected path
                              must start with a read-only command. Not a sandbox.

Decision is returned as hookSpecificOutput.permissionDecision (see code.claude.com/docs/en/hooks).
Fails closed: if the hook itself errors, the call is denied.
"""
from __future__ import annotations

import json
import os
import re
import shlex
import sys
from pathlib import Path

GOLDEN = "tests/golden/expected/"
VALIDATED = re.compile(r"(^|/)engine/(.+/)?validated/")
VALIDATED_IN_COMMAND = re.compile(r"(^|[\s/'\"=])engine/(\S+/)?validated/")
READ_ONLY = {"cat", "head", "tail", "less", "grep", "rg", "ls", "wc", "diff", "stat", "file", "sha256sum", "md5sum"}
READ_ONLY_GIT = {"diff", "log", "show", "status", "blame"}


def decide(decision: str, reason: str) -> None:
    print(json.dumps({"hookSpecificOutput": {
        "hookEventName": "PreToolUse", "permissionDecision": decision, "permissionDecisionReason": reason}}))


def rel(path: str, root: Path) -> str:
    p = Path(path.replace("\\", "/"))
    try:
        return p.resolve().relative_to(root.resolve()).as_posix()
    except ValueError:
        return p.as_posix()


def accepted_adr_for(relpath: str, root: Path) -> str | None:
    for adr in sorted((root / "docs" / "adr").glob("[0-9]*.md")):
        text = adr.read_text(errors="replace")
        if re.search(r"^Status:\s*Accepted\b", text, re.M | re.I) and relpath in text:
            return adr.name
    return None


def check_file(relpath: str, root: Path) -> tuple[str, str] | None:
    if relpath.startswith(GOLDEN):
        return ("deny", f"{relpath} is a frozen golden value. Golden diffs are findings to explain, not numbers "
                        "to update. If a change is truly intended, the owner deletes the file deliberately and "
                        "re-freezes with tools/freeze_golden.py.")
    if VALIDATED.search(relpath):
        adr = accepted_adr_for(relpath, root)
        if not adr:
            return ("deny", f"{relpath} is a validated model. Editing it needs an ADR in docs/adr/ with "
                            f"'Status: Accepted' that names this path. None found.")
    return None


def mentions_protected(segment: str) -> bool:
    return GOLDEN.rstrip("/") in segment or bool(VALIDATED_IN_COMMAND.search(segment))


def segment_is_read_only(segment: str) -> bool:
    try:
        words = shlex.split(segment)
    except ValueError:
        return False
    if not words:
        return True
    if words[0] == "git":
        return len(words) > 1 and words[1] in READ_ONLY_GIT
    return words[0] in READ_ONLY


def writes_via_shell(command: str) -> bool:
    """True if the command has an output redirection or tee outside quoted text."""
    lexer = shlex.shlex(command, posix=True, punctuation_chars=True)
    lexer.whitespace_split = True
    try:
        tokens = list(lexer)
    except ValueError:
        return True  # unbalanced quotes: can't tell, assume the worst
    for tok in tokens:
        # fd duplication such as 2>&1 lexes as "2", ">&", "1" and is not a write
        if tok == "tee" or (set(tok) <= set("<>&|") and ">" in tok and not tok.startswith(">&")):
            return True
    return False


def check_bash(command: str) -> tuple[str, str] | None:
    if not mentions_protected(command):
        return None
    if writes_via_shell(command):
        return ("deny", "Command writes (redirection/tee) and mentions a protected path "
                        "(tests/golden/expected/ or engine/**/validated/).")
    for segment in re.split(r"&&|\|\||;|\||\n", command):
        if mentions_protected(segment) and not segment_is_read_only(segment.strip()):
            return ("deny", f"Command segment touches a protected path and is not a known read-only command: "
                            f"{segment.strip()!r}. Protected: tests/golden/expected/, engine/**/validated/.")
    return None


def main() -> int:
    data = json.load(sys.stdin)
    root = Path(os.environ.get("CLAUDE_PROJECT_DIR") or data.get("cwd") or ".")
    tool, tool_input = data.get("tool_name"), data.get("tool_input") or {}
    if tool == "Bash":
        verdict = check_bash(tool_input.get("command", ""))
    else:
        path = tool_input.get("file_path") or tool_input.get("notebook_path")
        verdict = check_file(rel(path, root), root) if path else None
    if verdict:
        decide(*verdict)
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as exc:  # fail closed
        decide("deny", f"protect_paths hook error, denying to be safe: {exc!r}")
        sys.exit(0)
