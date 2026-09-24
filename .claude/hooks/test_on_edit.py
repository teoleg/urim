#!/usr/bin/env python3
"""PostToolUse hook: run the test suite after Claude edits engine, tests or tools.

On failure returns top-level {"decision": "block", "reason": ...}, which puts the failing
output next to the tool result so Claude sees it immediately (code.claude.com/docs/en/hooks).
Only fires for Edit/Write; Bash-driven file changes are not covered.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

WATCHED_PREFIXES = ("engine/", "tests/", "tools/")
WATCHED_FILES = ("pyproject.toml",)
MAX_REASON = 4000


def main() -> int:
    data = json.load(sys.stdin)
    root = Path(os.environ.get("CLAUDE_PROJECT_DIR") or data.get("cwd") or ".").resolve()
    path = (data.get("tool_input") or {}).get("file_path")
    if not path:
        return 0
    try:
        relpath = Path(path.replace("\\", "/")).resolve().relative_to(root).as_posix()
    except ValueError:
        return 0
    if not (relpath.startswith(WATCHED_PREFIXES) or relpath in WATCHED_FILES):
        return 0

    venv_python = root / ".venv" / "bin" / "python"
    python = str(venv_python) if venv_python.exists() else sys.executable
    proc = subprocess.run([python, "-m", "pytest", "-q", "-x", "-p", "no:cacheprovider"],
                          cwd=root, capture_output=True, text=True, timeout=110)
    if proc.returncode != 0:
        output = (proc.stdout + proc.stderr)[-MAX_REASON:]
        print(json.dumps({"decision": "block",
                          "reason": f"Tests failed after editing {relpath}. Fix before moving on.\n\n{output}"}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
