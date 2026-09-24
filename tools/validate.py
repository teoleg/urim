"""Run all checks and record a validation stamp tied to the current git commit.

Usage:
  python tools/validate.py              run tests (incl. Thummim's verify.py), write stamp
  python tools/validate.py --invalidate delete the stamp (e.g. Thummim agent review said FAIL)

The stamp is local evidence (gitignored). tools/deploy_gate.py reads it.
"""
from __future__ import annotations

import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
STAMP = ROOT / "verification" / "stamp.json"


def git(*args: str) -> str:
    return subprocess.run(["git", *args], cwd=ROOT, capture_output=True, text=True, check=True).stdout.strip()


def head_and_dirty() -> tuple[str, bool]:
    return git("rev-parse", "HEAD"), bool(git("status", "--porcelain"))


def run(cmd: list[str]) -> tuple[bool, str]:
    proc = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True, timeout=900)
    return proc.returncode == 0, (proc.stdout + proc.stderr)[-2000:]


def main(argv: list[str]) -> int:
    if argv == ["--invalidate"]:
        STAMP.unlink(missing_ok=True)
        print("stamp removed")
        return 0
    commit, dirty = head_and_dirty()
    tests_ok, tests_out = run([sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider"])
    verify_ok, verify_out = run([sys.executable, "verification/verify.py"])
    stamp = {
        "commit": commit,
        "dirty": dirty,
        "tests_passed": tests_ok,
        "thummim_verify_passed": verify_ok,
        "thummim_report": "verification/report.md",
        "created_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }
    ok = tests_ok and verify_ok
    if ok:
        STAMP.write_text(json.dumps(stamp, indent=2) + "\n")
    else:
        STAMP.unlink(missing_ok=True)
    print(json.dumps(stamp, indent=2))
    if not tests_ok:
        print("\n--- tests ---\n" + tests_out)
    if not verify_ok:
        print("\n--- thummim verify.py ---\n" + verify_out)
    print(f"\nVALIDATION: {'PASS' if ok else 'FAIL'}" + (" (working tree dirty: commit before deploying)" if ok and dirty else ""))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
