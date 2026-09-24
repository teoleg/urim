#!/usr/bin/env python3
"""Print every registered convention pack as JSON (injected into the conventions skill)."""
import json

from engine.conventions.packs import PACKS

print(json.dumps({name: pack.to_dict() for name, pack in PACKS.items()}, indent=2))
