"""Verify a release's allowlisted files without dependencies or network access."""

import hashlib
import json
from pathlib import Path
import sys

root = Path(
    sys.argv[1] if len(sys.argv) > 1 else Path(__file__).resolve().parents[1]
).resolve()
manifest = root / "CHECKSUMS.json"
if not manifest.exists():
    raise SystemExit(
        "CHECKSUMS.json is supplied in the packaged release, not the development tree."
    )
checksums = json.loads(manifest.read_text(encoding="utf-8"))
failures = []
for relative, expected in checksums.items():
    path = (root / relative).resolve()
    if not path.is_relative_to(root) or not path.is_file():
        failures.append(relative + ": missing or unsafe path")
    elif hashlib.sha256(path.read_bytes()).hexdigest() != expected:
        failures.append(relative + ": checksum mismatch")
print(
    json.dumps(
        {"verified": not failures, "files": len(checksums), "failures": failures},
        indent=2,
    )
)
raise SystemExit(bool(failures))
