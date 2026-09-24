"""Refuse to deploy unless tests and Thummim passed on exactly the commit being deployed.

Usage: python tools/deploy_gate.py     exit 0 = may deploy, 1 = refused (reasons printed)
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from validate import STAMP, head_and_dirty  # noqa: E402


def reasons_to_refuse(stamp: dict | None, head: str, dirty: bool) -> list[str]:
    if stamp is None:
        return ["no validation stamp: run /validate first"]
    out = []
    if stamp.get("commit") != head:
        out.append(f"stamp is for commit {str(stamp.get('commit'))[:12]}, HEAD is {head[:12]}: run /validate again")
    if dirty or stamp.get("dirty"):
        out.append("working tree has uncommitted changes (now or when validated): commit, then /validate")
    if not stamp.get("tests_passed"):
        out.append("tests did not pass")
    if not stamp.get("thummim_verify_passed"):
        out.append("Thummim verification did not pass")
    return out


def main() -> int:
    stamp = json.loads(STAMP.read_text()) if STAMP.exists() else None
    head, dirty = head_and_dirty()
    reasons = reasons_to_refuse(stamp, head, dirty)
    if reasons:
        print("DEPLOY REFUSED")
        for r in reasons:
            print(f"- {r}")
        return 1
    print(f"DEPLOY ALLOWED for commit {head[:12]} (validated {stamp['created_at']})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
