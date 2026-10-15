#!/usr/bin/env python3
"""Run the bundled reader without pip, Node.js, or network access."""

import sys
from pathlib import Path

if sys.version_info < (3, 12):
    raise SystemExit("Principia-Legacy requires Python 3.12 or newer.")
root = Path(__file__).resolve().parent
sys.path.insert(0, str(root / "src"))
from principia_legacy.cli import main

raise SystemExit(main(["--root", str(root), *(sys.argv[1:] or ["serve", "--offline"])]))
