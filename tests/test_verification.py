"""Thummim's verdict is part of the test suite: any blocking failure fails the build."""
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def test_thummim_verdict_pass():
    proc = subprocess.run([sys.executable, str(ROOT / "verification" / "verify.py")],
                          cwd=ROOT, capture_output=True, text=True, timeout=300)
    assert proc.returncode == 0, (proc.stdout + proc.stderr)[-3000:]
