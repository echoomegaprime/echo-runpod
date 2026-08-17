#!/usr/bin/env python3
"""Regenerate nexus/capabilities.json from the canonical capability_records()."""

from __future__ import annotations

import json
from pathlib import Path

from echo_runpod.capabilities import nexus_manifest


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    dest = root / "nexus" / "capabilities.json"
    dest.write_text(json.dumps(nexus_manifest(), indent=2) + "\n", encoding="utf-8")
    print(dest)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
