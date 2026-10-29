#!/usr/bin/env python3
"""Open the lightweight reader against the configured private cloud staging API."""

import sys
from pathlib import Path

if sys.version_info < (3, 12):
    raise SystemExit("Principia-Legacy needs Python 3.12 or newer.")
root = Path(__file__).resolve().parent
sys.path.insert(0, str(root / "src"))
from principia_legacy.cloud import main  # noqa: E402 - load bundled source after path setup

main(root)
